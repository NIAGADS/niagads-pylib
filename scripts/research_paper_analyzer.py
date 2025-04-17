import PyPDF2
import re
from typing import Tuple, Optional, List, Dict
import json
import os
from datetime import datetime
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    BartForConditionalGeneration
)
from sentence_transformers import SentenceTransformer
from pdf2image import convert_from_path
import pytesseract
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class ExtractorAgent:
    def __init__(self):
        self.section_keywords = [
            'results', 'findings', 'conclusion', 'discussion',
            'results and discussion', 'findings and discussion',
            'main results', 'key findings', 'conclusions',
            'implications', 'significance', 'contribution',
            'take-home message', 'key points', 'summary'
        ]
        self.section_patterns = [
            r'(?i)(?:results|findings|conclusion|discussion)[\s:]*',
            r'(?i)(?:results and discussion|findings and discussion)[\s:]*',
            r'(?i)(?:main results|key findings|conclusions)[\s:]*',
            r'(?i)(?:implications|significance|contribution)[\s:]*',
            r'(?i)(?:take-home message|key points|summary)[\s:]*'
        ]
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        self.section_model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)
        self.previous_attempts = []
        self.problem_keywords = [
            'problem', 'challenge', 'issue', 'limitation', 'gap',
            'difficulty', 'obstacle', 'barrier', 'drawback',
            'shortcoming', 'weakness', 'deficiency'
        ]
        self.solution_keywords = [
            'solution', 'approach', 'method', 'technique',
            'propose', 'develop', 'introduce', 'present',
            'address', 'overcome', 'resolve', 'improve'
        ]

    def adjust_patterns_based_on_feedback(self, feedback: str) -> None:
        if "too short" in feedback.lower():
            self.section_patterns = [p.replace(r'[\s:]*', r'[\s:]+[\w\s]+[\s:]*') for p in self.section_patterns]
        
        if "different part" in feedback.lower():
            self.section_patterns.extend([
                r'(?i)(?:experimental results|data analysis|statistical analysis)[\s:]*',
                r'(?i)(?:quantitative results|qualitative findings)[\s:]*'
            ])
        
        if "no clear results" in feedback.lower():
            self.section_patterns.extend([
                r'(?i)(?:our analysis|the data|these observations)[\s:]*',
                r'(?i)(?:we observed|we found|the study shows)[\s:]*'
            ])

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            if len(text.strip()) < 100:
                images = convert_from_path(pdf_path)
                for image in images:
                    text += pytesseract.image_to_string(image) + "\n"
        except Exception as e:
            print(f"Error reading PDF: {str(e)}")
            return ""
        return text

    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        embeddings1 = self.sentence_model.encode(text1, convert_to_tensor=True)
        embeddings2 = self.sentence_model.encode(text2, convert_to_tensor=True)
        
        embeddings1 = embeddings1.cpu().numpy()
        embeddings2 = embeddings2.cpu().numpy()
        
        embeddings1 = embeddings1.reshape(1, -1)
        embeddings2 = embeddings2.reshape(1, -1)
        
        similarity = cosine_similarity(embeddings1, embeddings2)[0][0]
        return similarity

    def is_results_section(self, text: str) -> bool:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.section_model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=1)
            return predictions[0][1].item() > 0.5

    def find_conclusion_indicators(self, text: str) -> List[str]:
        conclusion_patterns = [
            r'(?:we|this study|our results|the data|these findings|this research) (?:show|demonstrate|indicate|suggest|reveal|propose|conclude|find|establish|confirm|support|provide evidence)',
            r'(?:in conclusion|to conclude|in summary|overall|taken together|collectively|these results)',
            r'(?:the main|key|important|significant|major) (?:finding|result|conclusion|implication)',
            r'(?:this|our) (?:work|study|research) (?:contributes|advances|improves|enhances)',
            r'(?:therefore|thus|hence|consequently|as a result)'
        ]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        conclusion_sentences = []
        
        for sentence in sentences:
            for pattern in conclusion_patterns:
                if re.search(pattern, sentence.lower()):
                    conclusion_sentences.append(sentence.strip())
                    break
        
        return conclusion_sentences

    def find_problem_solution_sections(self, text: str) -> Tuple[List[str], List[str]]:
        problem_sentences = []
        solution_sentences = []
        
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para in paragraphs:
            if any(keyword in para.lower() for keyword in self.problem_keywords):
                problem_sentences.extend(re.split(r'(?<=[.!?])\s+', para))
            
            if any(keyword in para.lower() for keyword in self.solution_keywords):
                solution_sentences.extend(re.split(r'(?<=[.!?])\s+', para))
        
        return problem_sentences, solution_sentences

    def find_section(self, text: str, feedback: Optional[str] = None) -> Tuple[Optional[str], str]:
        if feedback:
            self.adjust_patterns_based_on_feedback(feedback)
            for prev_section, prev_text in self.previous_attempts:
                text = text.replace(prev_text, "")

        sections = []
        for pattern in self.section_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                start_pos = match.end()
                next_section = re.search(r'(?i)(?:methods|references|acknowledgements|appendix)[\s:]*', text[start_pos:])
                if next_section:
                    section_text = text[start_pos:start_pos + next_section.start()]
                else:
                    section_text = text[start_pos:]
                
                if len(section_text.strip()) > 100:
                    similarity_score = self.calculate_semantic_similarity(
                        section_text,
                        "The results show that our findings indicate significant improvements in the experimental group."
                    )
                    
                    is_results = self.is_results_section(section_text)
                    
                    conclusion_sentences = self.find_conclusion_indicators(section_text)
                    conclusion_score = len(conclusion_sentences) / 10
                    
                    score = (similarity_score * 0.3 + is_results * 0.3 + conclusion_score * 0.4)
                    
                    sections.append((score, match.group(0).strip(), section_text.strip()))

        sections.sort(reverse=True, key=lambda x: x[0])
        top_sections = sections[:3]
        
        if top_sections:
            combined_text = "\n\n".join(section[2] for section in top_sections)
            self.previous_attempts.extend([(section[1], section[2]) for section in top_sections])
            return top_sections[0][1], combined_text

        for keyword in self.section_keywords:
            if keyword in text.lower():
                start_pos = text.lower().find(keyword)
                section_text = text[start_pos:start_pos + 2000]
                self.previous_attempts.append((keyword, section_text))
                return keyword, section_text.strip()

        return None, ""

    def analyze_paper(self, pdf_path: str, feedback: Optional[str] = None) -> Tuple[Optional[str], str]:
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return None, "Could not extract text from PDF"
        
        section_name, section_text = self.find_section(text, feedback)
        if not section_text:
            return None, "Could not find relevant section in the paper"
        
        return section_name, section_text

class VerifierAgent:
    def __init__(self):
        self.indicators = {
            'positive': [
                'results show', 'findings indicate', 'conclusion suggests',
                'data demonstrate', 'analysis reveals', 'study found',
                'research shows', 'experiments show', 'we found',
                'statistically significant', 'p-value', 'confidence interval',
                'we conclude', 'our results suggest', 'this study demonstrates',
                'the main finding', 'key contribution', 'important implication',
                'significant result', 'major conclusion', 'take-home message'
            ],
            'negative': [
                'introduction', 'methods', 'materials', 'background',
                'literature review', 'future work', 'limitations',
                'acknowledgements', 'references'
            ]
        }

        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        self.section_model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)

        self.summarizer_tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
        self.summarizer_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

        self.polisher_tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
        self.polisher_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
        
        self.problem_keywords = [
            'problem', 'challenge', 'issue', 'limitation', 'gap',
            'difficulty', 'obstacle', 'barrier', 'drawback',
            'shortcoming', 'weakness', 'deficiency'
        ]
        self.solution_keywords = [
            'solution', 'approach', 'method', 'technique',
            'propose', 'develop', 'introduce', 'present',
            'address', 'overcome', 'resolve', 'improve'
        ]

    def find_conclusion_indicators(self, text: str) -> List[str]:
        conclusion_patterns = [
            r'(?:we|this study|our results|the data|these findings|this research) (?:show|demonstrate|indicate|suggest|reveal|propose|conclude|find|establish|confirm|support|provide evidence)',
            r'(?:in conclusion|to conclude|in summary|overall|taken together|collectively|these results)',
            r'(?:the main|key|important|significant|major) (?:finding|result|conclusion|implication)',
            r'(?:this|our) (?:work|study|research) (?:contributes|advances|improves|enhances)',
            r'(?:therefore|thus|hence|consequently|as a result)'
        ]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        conclusion_sentences = []
        
        for sentence in sentences:
            for pattern in conclusion_patterns:
                if re.search(pattern, sentence.lower()):
                    conclusion_sentences.append(sentence.strip())
                    break
        
        return conclusion_sentences

    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        embeddings1 = self.sentence_model.encode(text1, convert_to_tensor=True)
        embeddings2 = self.sentence_model.encode(text2, convert_to_tensor=True)
        
        embeddings1 = embeddings1.cpu().numpy()
        embeddings2 = embeddings2.cpu().numpy()
        
        embeddings1 = embeddings1.reshape(1, -1)
        embeddings2 = embeddings2.reshape(1, -1)
        
        similarity = cosine_similarity(embeddings1, embeddings2)[0][0]
        return similarity

    def calculate_section_quality(self, section_text: str) -> float:
        reference_text = "The results demonstrate significant findings with statistical significance."
        similarity_score = self.calculate_semantic_similarity(section_text, reference_text)
        
        positive_count = sum(1 for indicator in self.indicators['positive'] 
                           if indicator.lower() in section_text.lower())
        
        length_score = min(len(section_text) / 2000, 1.0)
        
        return (similarity_score * 0.4 + positive_count * 0.3 + length_score * 0.3)

    def verify_section(self, section_name: str, section_text: str) -> Tuple[bool, str]:
        quality_score = self.calculate_section_quality(section_text)
        
        if quality_score < 0.5:
            return False, f"Section quality score too low: {quality_score:.2f}"
        
        if len(section_text) < 200:
            return False, "Section is too short to be a proper results section"
        
        inputs = self.tokenizer(section_text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.section_model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=1)
            if predictions[0][1].item() < 0.5:
                return False, "AI model indicates this is not a results section"
        
        return True, "Section appears to be valid"

    def find_problem_solution_sections(self, text: str) -> Tuple[List[str], List[str]]:
        problem_sentences = []
        solution_sentences = []
        
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para in paragraphs:
            if any(keyword in para.lower() for keyword in self.problem_keywords):
                problem_sentences.extend(re.split(r'(?<=[.!?])\s+', para))
            
            if any(keyword in para.lower() for keyword in self.solution_keywords):
                solution_sentences.extend(re.split(r'(?<=[.!?])\s+', para))
        
        return problem_sentences, solution_sentences

    def generate_summary(self, section_text: str) -> str:
        problem_sentences, solution_sentences = self.find_problem_solution_sections(section_text)
        
        conclusion_sentences = self.find_conclusion_indicators(section_text)
        
        inputs = self.summarizer_tokenizer(section_text, return_tensors="pt", truncation=True, max_length=1024)
        with torch.no_grad():
            summary_ids = self.summarizer_model.generate(
                inputs["input_ids"],
                max_length=600,
                min_length=100,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )
        summary = self.summarizer_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        structured_summary = []
        
        if problem_sentences:
            structured_summary.append("\nProblems Addressed:")
            for sentence in problem_sentences[:3]: 
                if sentence not in summary:
                    structured_summary.append(f"- {sentence}")
        
        if solution_sentences:
            structured_summary.append("\nSolutions Proposed:")
            for sentence in solution_sentences[:3]:
                if sentence not in summary:
                    structured_summary.append(f"- {sentence}")
        
        if conclusion_sentences:
            structured_summary.append("\nKey Conclusions:")
            for sentence in conclusion_sentences:
                if sentence not in summary:
                    structured_summary.append(f"- {sentence}")
        
        full_summary = summary + "\n" + "\n".join(structured_summary)
        
        polished_summary = self.polish_summary(full_summary)
        
        return polished_summary

    def polish_summary(self, summary: str) -> str:
        inputs = self.polisher_tokenizer(
            summary,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        )
        
        with torch.no_grad():
            polished_ids = self.polisher_model.generate(
                inputs["input_ids"],
                max_length=400,
                min_length=200,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3
            )
        
        polished = self.polisher_tokenizer.decode(polished_ids[0], skip_special_tokens=True)
        return polished

class ResearchPaperAnalyzer:
    def __init__(self):
        self.extractor = ExtractorAgent()
        self.verifier = VerifierAgent()
        self.max_iterations = 4

    def analyze_paper_with_verification(self, pdf_path: str) -> Optional[str]:
        feedback = None
        for iteration in range(self.max_iterations):
            print(f"\nIteration {iteration + 1}:")
            if feedback:
                print(f"Using feedback from previous attempt: {feedback}")
            
            section_name, section_text = self.extractor.analyze_paper(pdf_path, feedback)
            if not section_text:
                print("Could not extract any text from the paper")
                return None
            
            print(f"Found section: {section_name}")
            
            is_valid, feedback = self.verifier.verify_section(section_name, section_text)
            if is_valid:
                print("Section verified successfully!")
                summary = self.verifier.generate_summary(section_text)
                return summary
            else:
                print(f"Verification failed: {feedback}")
                if iteration < self.max_iterations - 1:
                    print("Trying to find a better section...")
                else:
                    print("Maximum iterations reached. Using best available section.")
                    summary = self.verifier.generate_summary(section_text)
                    return summary
        
        return None

    def save_summary(self, summary: str, pdf_path: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "paper_summaries"
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_name = os.path.basename(pdf_path)
        output_file = os.path.join(output_dir, f"{pdf_name}_{timestamp}_summary.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        return output_file

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze research papers using AI agents to extract and summarize results/findings sections.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'pdf_path',
        help='Path to the PDF file to analyze',
        type=str
    )
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: The file '{args.pdf_path}' does not exist.")
        return
    
    if not args.pdf_path.lower().endswith('.pdf'):
        print(f"Error: '{args.pdf_path}' is not a PDF file.")
        return
    
    analyzer = ResearchPaperAnalyzer()
    summary = analyzer.analyze_paper_with_verification(args.pdf_path)
    
    if summary:
        output_file = analyzer.save_summary(summary, args.pdf_path)
        print(f"\nSummary saved to: {output_file}")
        print("\nSummary content:")
        print(summary)
    else:
        print("Failed to generate summary")

if __name__ == "__main__":
    main() 