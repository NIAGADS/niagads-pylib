import PyPDF2
import re
from typing import Tuple, Optional, List, Dict
import json
import os
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModel, pipeline
from sentence_transformers import SentenceTransformer
from pdf2image import convert_from_path
import pytesseract
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import argparse

class ExtractorAgent:
    def __init__(self):
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm = pipeline("text-generation", model="gpt2")
        self.previous_attempts = []

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

    def identify_sections(self, text: str) -> List[str]:
        chunk_size = 2000
        overlap = 500
        chunks = []
        
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)
        
        all_sections = set()
        
        for chunk in chunks:
            prompt = f"""Given the following research paper text, identify the main sections and their order. 
            Return only the section names in order, separated by commas. Do not include any other text.
            Focus on identifying standard research paper sections like Abstract, Introduction, Methods, Results, Discussion, etc.
            
            Text:
            {chunk}
            """
            
            response = self.llm(
                prompt,
                max_new_tokens=100,
                num_return_sequences=1,
                temperature=0.7,
            )
            
            sections = response[0]["generated_text"].strip().split(',')
            all_sections.update(section.strip().lower() for section in sections)
        
        section_order = {
            'abstract': 0,
            'introduction': 1,
            'background': 2,
            'methods': 3,
            'materials and methods': 3,
            'results': 4,
            'findings': 4,
            'discussion': 5,
            'conclusion': 6,
            'references': 7,
            'acknowledgments': 8,
            'supplementary': 9,
            'appendix': 10
        }
        
        sorted_sections = sorted(
            all_sections,
            key=lambda x: section_order.get(x, 999)
        )
        
        return sorted_sections

    def extract_headers(self, text: str) -> List[Dict[str, str]]:
        header_pattern = r'(?i)^\s*(?:\d+\.\s*)?([A-Z][A-Za-z]+)(?:\s*:)?\s*$'
        
        lines = text.split('\n')
        headers = []
        
        expected_sections = self.identify_sections(text)
        
        for i, line in enumerate(lines):
            match = re.match(header_pattern, line.strip())
            if match:
                header_text = match.group(1).strip()
                context = '\n'.join(lines[i+1:i+4])
                
                similarities = []
                for section in expected_sections:
                    section_words = section.split()
                    for word in section_words:
                        similarity = self.calculate_semantic_similarity(header_text.lower(), word)
                        similarities.append((word, similarity))
                
                similarities.sort(key=lambda x: x[1], reverse=True)
                
                headers.append({
                    'text': header_text,
                    'context': context,
                    'most_similar': similarities[0][0],
                    'similarity_score': float(similarities[0][1])
                })
        
        return headers

    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        embeddings1 = self.sentence_model.encode(text1, convert_to_tensor=True)
        embeddings2 = self.sentence_model.encode(text2, convert_to_tensor=True)
        
        embeddings1 = embeddings1.cpu().numpy()
        embeddings2 = embeddings2.cpu().numpy()
        
        embeddings1 = embeddings1.reshape(1, -1)
        embeddings2 = embeddings2.reshape(1, -1)
        
        similarity = cosine_similarity(embeddings1, embeddings2)[0][0]
        return float(similarity)

    def analyze_findings(self, text: str, headers: List[Dict[str, str]]) -> str:
        header_texts = [h['original'] for h in headers]
        
        chunk_size = 5
        header_chunks = [header_texts[i:i + chunk_size] for i in range(0, len(header_texts), chunk_size)]
        
        findings_sections = set()
        for chunk in header_chunks:
            prompt = f"""Given these section headers from a research paper: {', '.join(chunk)}
            Which sections are most likely to contain the authors' findings, conclusions, or key results? 
            Return only single words, separated by commas."""
            
            try:
                response = self.llm(
                    prompt,
                    max_new_tokens=50,
                    num_return_sequences=1,
                    temperature=0.7,
                )
                sections = response[0]["generated_text"].strip().split(',')
                findings_sections.update(s.strip().lower() for s in sections)
            except Exception as e:
                print(f"Warning: Error processing header chunk: {str(e)}")
                continue
        
        findings_content = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            match = re.match(r'(?i)^\s*(?:\d+\.\s*)?([A-Z][A-Za-z]+)(?:\s*:)?\s*$', line.strip())
            if match:
                header_text = match.group(1).strip().lower()
                if any(self.calculate_semantic_similarity(header_text, section) > 0.7 for section in findings_sections):
                    content = []
                    j = i + 1
                    while j < len(lines) and not re.match(r'(?i)^\s*(?:\d+\.\s*)?([A-Z][A-Za-z]+)(?:\s*:)?\s*$', lines[j].strip()):
                        content.append(lines[j])
                        j += 1
                    findings_content.append({
                        'header': header_text,
                        'content': '\n'.join(content)
                    })
        
        if findings_content:
            chunk_size = 1000 
            summaries = []
            
            for content in findings_content:
                text_chunks = [content['content'][i:i + chunk_size] for i in range(0, len(content['content']), chunk_size)]
                
                for chunk in text_chunks:
                    try:
                        summary_prompt = f"""Given the following section from a research paper, provide a detailed summary of the authors' key findings and conclusions. 
                        Focus on the main results, implications, and conclusions. Be specific and include any quantitative results if present.
                        
                        Section: {content['header']}
                        Content:
                        {chunk}
                        """
                        
                        response = self.llm(
                            summary_prompt,
                            max_new_tokens=200,
                            num_return_sequences=1,
                            temperature=0.7,
                        )
                        
                        summaries.append(response[0]["generated_text"].strip())
                    except Exception as e:
                        print(f"Warning: Error processing content chunk: {str(e)}")
                        continue
            
            if summaries:
                final_prompt = f"""Combine these summaries of research findings into a coherent, detailed summary:
                {' '.join(summaries)}"""
                
                try:
                    response = self.llm(
                        final_prompt,
                        max_new_tokens=300,
                        num_return_sequences=1,
                        temperature=0.7,
                    )
                    return response[0]["generated_text"].strip()
                except Exception as e:
                    print(f"Warning: Error combining summaries: {str(e)}")
                    return " ".join(summaries)
            
        return "No findings sections were identified in the paper."

class VerifierAgent:
    def __init__(self):
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm = pipeline("text-generation", model="gpt2")

    def verify_headers(self, headers: List[Dict[str, str]]) -> Tuple[bool, List[Dict[str, str]]]:
        verified_headers = []
        
        header_texts = [h['text'] for h in headers]
        prompt = f"""Given these section headers from a research paper: {', '.join(header_texts)}
        Does this paper have a complete structure? Answer with only 'yes' or 'no'."""
        
        response = self.llm(
            prompt,
            max_new_tokens=10,
            num_return_sequences=1,
            temperature=0.7,
        )
        
        is_complete = response[0]["generated_text"].strip().lower().startswith('yes')
        
        for header in headers:
            if header['similarity_score'] > 0.7:
                verified_headers.append({
                    'original': header['text'],
                    'verified_as': header['most_similar'],
                    'confidence': float(header['similarity_score']),
                    'context': header['context']
                })
        
        return is_complete, verified_headers

class ResearchPaperAnalyzer:
    def __init__(self):
        self.extractor = ExtractorAgent()
        self.verifier = VerifierAgent()

    def analyze_paper(self, pdf_path: str) -> Tuple[bool, List[Dict[str, str]], str]:
        text = self.extractor.extract_text_from_pdf(pdf_path)
        if not text:
            return False, [], "Failed to extract text from PDF"
        
        headers = self.extractor.extract_headers(text)
        is_complete, verified_headers = self.verifier.verify_headers(headers)
        findings_summary = self.extractor.analyze_findings(text, verified_headers)
        
        return is_complete, verified_headers, findings_summary

    def save_analysis(self, is_complete: bool, headers: List[Dict[str, str]], findings_summary: str, pdf_path: str) -> Tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "paper_analysis"
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_name = os.path.basename(pdf_path)
        json_file = os.path.join(output_dir, f"{pdf_name}_{timestamp}_analysis.json")
        summary_file = os.path.join(output_dir, f"{pdf_name}_{timestamp}_summary.txt")
        
        analysis = {
            'is_complete': is_complete,
            'headers': headers,
            'findings_summary': findings_summary,
            'timestamp': timestamp
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Research Paper Analysis Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write("Key Findings and Conclusions:\n")
            f.write("-" * 30 + "\n")
            f.write(findings_summary)
        
        return json_file, summary_file

def main():
    parser = argparse.ArgumentParser(
        description='Analyze research papers using AI to extract and verify section headers.',
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
    is_complete, headers, findings_summary = analyzer.analyze_paper(args.pdf_path)
    
    if headers:
        json_file, summary_file = analyzer.save_analysis(is_complete, headers, findings_summary, args.pdf_path)
        print(f"\nAnalysis saved to: {json_file}")
        print(f"Summary saved to: {summary_file}")
        print("\nFound headers:")
        for header in headers:
            print(f"- {header['original']} (verified as: {header['verified_as']}, confidence: {header['confidence']:.2f})")
        print("\nKey Findings and Conclusions:")
        print(findings_summary)
    else:
        print("Failed to extract any headers from the paper")

if __name__ == "__main__":
    main() 