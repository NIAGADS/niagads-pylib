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
        # Check if CUDA is available and use GPU if it is
        device = 0 if torch.cuda.is_available() else -1
        self.llm = pipeline("text-generation", model="gpt2", device=device)
        self.previous_attempts = []
        self.max_tokens = 1024  # GPT-2's context window
        self.chunk_overlap = 100  # Overlap between chunks

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

    def chunk_text(self, text: str, chunk_size: int = None) -> List[str]:
        """Split text into chunks that fit within the model's context window."""
        if chunk_size is None:
            chunk_size = self.max_tokens - 200  # Leave room for prompt and response
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]
            
            # Try to find a good breaking point (e.g., paragraph or sentence end)
            if end < text_length:
                last_paragraph = chunk.rfind('\n\n')
                last_sentence = max(
                    chunk.rfind('. '),
                    chunk.rfind('! '),
                    chunk.rfind('? ')
                )
                break_point = max(last_paragraph, last_sentence)
                
                if break_point > 0:
                    end = start + break_point + 1
                    chunk = text[start:end]
            
            chunks.append(chunk)
            start = end - self.chunk_overlap if end < text_length else end
        
        return chunks

    def identify_sections(self, text: str) -> List[str]:
        chunks = self.chunk_text(text)
        all_sections = set()
        
        for chunk in chunks:
            prompt = f"""You are a domain-expert NLP assistant specialized in parsing biomedical research articles (e.g., PubMed abstracts and full texts). Your goal is to locate only the **primary, top-level** section headings, in the exact order they appear in the text, and output them **as a single comma-separated list**. Do not output anything else.

            === INSTRUCTIONS ===
            1. **Scope of sections**  
            - Recognize standard IMRaD headings. Some examples include: Abstract, Introduction, Methods (or Materials and Methods), Results, Discussion, Conclusion(s).  
            - Also handle structured abstract labels (Background, Objective, Design, Setting, Participants, Interventions, Main Outcome Measures, Results, Conclusion).  
            - Include other common headings if present: "Graphical Abstract," "Data Availability," "Funding," "Acknowledgments," "References," "Supplementary Material."  
            - **Ignore** subsection labels (e.g. "2.1 Study Population") and in-line mentions of methods/results.

            2. **Formatting rules**  
            - Output exactly one line: the list of section names, **in the order they appear**, separated by commas and a single space.  
            - **Do not** include any additional words, numbers, colons, or punctuation.  
            - If a heading appears more than once, list it only on its first occurrence.  
            - If no recognizable headings are found, output: `Unknown`.

            3. **Robustness tips**  
            - Headings may be in ALL CAPS, Title Case, or sentence case—detect them regardless of capitalization.  
            - They may be followed by a line break, a horizontal rule, or a blank line.  
            - There may be PDF-to-text artifacts (extra whitespace, missing colons)—use context to infer true headings.

            === INPUT ===

            Text:
            {chunk}"""
            
            try:
                response = self.llm(
                    prompt,
                    max_new_tokens=100,
                    num_return_sequences=1,
                    temperature=0.7,
                )
                sections = response[0]["generated_text"].strip().split(',')
                all_sections.update(section.strip().lower() for section in sections)
            except Exception as e:
                print(f"Warning: Error processing chunk: {str(e)}")
                continue
        
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
            prompt = f"""
            You are a domain-expert NLP assistant specialized in analyzing the structure of scientific papers. Given only a flat list of section headers (and possible non-header strings) from a research article, your task is to pick out which ones are most likely to contain the authors' findings, conclusions, or key results.

            === INSTRUCTIONS ===
            1. **Filter out noise**  
            - The input list may include items that are not actual section headers (e.g., running headers, footnotes, page numbers, figure/table captions).  
            - Ignore any entry that doesn't correspond to a top-level section heading.

            2. **Target sections**  
            - From the remaining items, choose those most likely to hold results or wrap up the study: Results, Findings, Discussion, Conclusion, Summary, Interpretation.  
            - Also consider synonyms in structured abstracts: "Key Findings," "Principal Results," or "Concluding Remarks."  

            3. **Formatting rules**  
            - Return **only** the chosen section names as **single words**, in **Title Case** (e.g., Results, Discussion).  
            - If a header is multi-word (e.g. "Key Findings"), extract only the core noun ("Findings").  
            - Preserve the **order** in which these valid headers appeared in the input list.  
            - Separate each by a comma and a single space; do **not** add any other punctuation, numbers, or commentary.  
            - If none match, output `None`.

            4. **Robustness tips**  
            - Match headings case-insensitively and trim any surrounding whitespace or stray punctuation.  
            - Deduplicate: if the same core noun appears multiple times, list it only once.

            === INPUT ===  
                        
            These are the section headers from a research paper: {', '.join(chunk)}"""
            
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
                        summary_prompt = f"""You are a domain-expert NLP assistant specialized in parsing and summarizing biomedical research articles. Your goal is to read **only** the single section of a paper specified by its header and produce a concise, detailed summary of the authors' key findings and conclusions from that section.

                        === INSTRUCTIONS ===
                        1. **Scope of analysis**  
                        - **Only** consider the content provided under the given section header; do not infer or include information from any other parts of the paper.  
                        - If the content does not correspond to the specified header, treat it as noise and ignore it.

                        2. **Scope of summary**  
                        - Extract and synthesize the authors' main results, quantitative metrics (e.g., effect sizes, p-values, confidence intervals), and stated conclusions **present in this section**.  
                        - Highlight any implications for the field, stated limitations, and potential future directions if mentioned **within this section**.  

                        3. **Formatting rules**  
                        - Return your summary in **three paragraphs**:  
                            1. **Key Results**: 2–4 sentences detailing the primary quantitative and qualitative findings in this section. If no quantitative data are present, state "No quantitative data reported."  
                            2. **Implications**: 2–4 sentences on what these section-specific results mean for practice, theory, or further research.  
                            3. **Conclusions**: 2–4 sentences wrap-up of the authors' final statements or recommendations **drawn solely from this section**.  
                        - **Do not** include any headings, labels (e.g., "Paragraph 1"), or extra commentary.  

                        4. **Robustness tips**  
                        - Interpret statistical notation (e.g., "p<0.05", "HR=1.7 [95% CI 1.2–2.4]") found in this section.  
                        - Merge closely related findings into a single bullet or sentence.  
                        - Omit any methods or background details unless they directly influence interpretation of results in this section.

                        === INPUT ===  
                        
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
                final_prompt = f"""You are a domain-expert NLP assistant specialized in synthesizing and integrating scientific content. Given a list of individual summary fragments of research findings, your task is to merge them into a single, coherent, detailed summary that reads like a unified narrative.

                === INSTRUCTIONS ===
                1. **Scope of synthesis**  
                - Consider **only** the provided summary fragments. Do not introduce new information or external references.  
                - Preserve each fragment's key findings, quantitative results, and conclusions.

                2. **Merging strategy**  
                - Identify overlaps and redundancies across fragments and merge similar points into unified statements.  
                - Arrange content into a logical flow: start with background/context (if any), then present major results in descending order of importance, followed by implications and conclusions.  
                - Use transitional phrases (e.g., "Furthermore," "In addition," "Consequently") to link ideas smoothly.

                3. **Formatting rules**  
                - Output as **one cohesive narrative** in **3–5 paragraphs**:  
                    1. **Overview**: 1–2 sentences introducing the combined scope and purpose.  
                    2. **Key Findings**: 2–4 sentences summarizing the main quantitative and qualitative results.  
                    3. **Implications**: 2–4 sentences on the significance and potential applications.  
                    4. **Conclusions and Future Directions**: 1–2 sentences wrapping up and noting any recommended next steps.  
                - Do **not** list bullet points or use headings—write continuous prose.  
                - Retain any numerical values and statistical measures verbatim from the fragments.

                4. **Robustness tips**  
                - If two fragments report the same result with slightly different wording, consolidate them into a single clear statement.  
                - Maintain any acronyms or domain-specific terms used in the fragments.  
                - Ensure no key finding is lost—every distinct result in the inputs must appear in the synthesis.

                === INPUT ===  
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
        # Check if CUDA is available and use GPU if it is
        device = 0 if torch.cuda.is_available() else -1
        self.llm = pipeline("text-generation", model="gpt2", device=device)
        self.findings_keywords = {
            'results', 'findings', 'conclusion', 'discussion', 'summary', 
            'interpretation', 'key findings', 'principal results', 'concluding remarks'
        }

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

    def verify_findings_headers(self, headers: List[Dict[str, str]], text: str) -> List[Dict[str, str]]:
        verified_findings_headers = []
        
        for header in headers:
            header_text = header['text'].lower()
            
            is_findings_header = any(keyword in header_text for keyword in self.findings_keywords)
            
            if is_findings_header:
                prompt = f"""You are a domain-expert NLP verifier agent whose job is to assess whether a single section of a research paper contains the authors' actual findings, conclusions, or key results.

                === INSTRUCTIONS ===
                1. **Scope of analysis**  
                - Consider **only** the provided section header and its content. Do not infer from other parts of the paper.  
                - Ignore any methods details, background context, or metadata unless they explicitly state results or conclusions.

                2. **Define "findings/conclusions/key results"**  
                - Look for statements of experimental or observational outcomes (e.g., "we found," "results show," quantitative metrics).  
                - Identify summary judgments or take-home messages (e.g., "these data suggest," "we conclude that").  
                - Exclude descriptions of methods, objectives, or literature review.

                3. **Formatting rules**  
                - Answer **only** with `yes` if the section contains one or more actual findings, conclusions, or key results; otherwise answer `no`.  
                - Do **not** output any additional words, punctuation, or explanation.

                4. **Robustness tips**  
                - Match language case-insensitively and trim whitespace.  
                - Treat statistical expressions (e.g., "p<0.05," "OR=2.3 [95% CI 1.5–3.6]") as evidence of findings.  
                - If the content only restates aims or methods, answer `no`.

                === INPUT ===  
                Header: {header['text']}
                Content: {header['context']}"""
                
                try:
                    response = self.llm(
                        prompt,
                        max_new_tokens=10,
                        num_return_sequences=1,
                        temperature=0.7,
                    )
                    
                    contains_findings = response[0]["generated_text"].strip().lower().startswith('yes')
                    
                    if contains_findings:
                        verified_findings_headers.append({
                            'original': header['text'],
                            'verified_as': 'findings_section',
                            'confidence': float(header['similarity_score']),
                            'context': header['context']
                        })
                except Exception as e:
                    print(f"Warning: Error verifying findings header: {str(e)}")
                    continue
        
        return verified_findings_headers

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
        
        findings_headers = self.verifier.verify_findings_headers(verified_headers, text)
        
        findings_summary = self.extractor.analyze_findings(text, findings_headers)
        
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