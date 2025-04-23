import PyPDF2
import re
from typing import Tuple, Optional, List, Dict
import json
import os
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
from pdf2image import convert_from_path
import pytesseract
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import argparse

class ExtractorAgent:
    def __init__(self):
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.sapbert_tokenizer = AutoTokenizer.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
        self.sapbert_model = AutoModel.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
        self.previous_attempts = []
        
        self.common_headers = [
            'abstract', 'introduction', 'background', 'methods', 'materials and methods',
            'results', 'findings', 'discussion', 'conclusion', 'references',
            'acknowledgments', 'supplementary', 'appendix'
        ]

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

    def extract_headers(self, text: str) -> List[Dict[str, str]]:
        header_pattern = r'(?i)^\s*(?:\d+\.\s*)?([A-Z][A-Za-z\s]+)(?:\s*:)?\s*$'
        
        lines = text.split('\n')
        headers = []
        
        for i, line in enumerate(lines):
            match = re.match(header_pattern, line.strip())
            if match:
                header_text = match.group(1).strip()
                
                context = '\n'.join(lines[i+1:i+4])
                
                similarities = []
                for common_header in self.common_headers:
                    similarity = self.calculate_semantic_similarity(header_text.lower(), common_header)
                    similarities.append((common_header, similarity))
                
                similarities.sort(key=lambda x: x[1], reverse=True)
                
                headers.append({
                    'text': header_text,
                    'context': context,
                    'most_similar': similarities[0][0],
                    'similarity_score': similarities[0][1]
                })
        
        return headers

class VerifierAgent:
    def __init__(self):
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.sapbert_tokenizer = AutoTokenizer.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
        self.sapbert_model = AutoModel.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
        
        self.expected_sections = [
            'abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion'
        ]

    def verify_headers(self, headers: List[Dict[str, str]]) -> Tuple[bool, List[Dict[str, str]]]:
        verified_headers = []
        missing_sections = set(self.expected_sections)
        
        for header in headers:
            if header['similarity_score'] > 0.7: 
                verified_headers.append({
                    'original': header['text'],
                    'verified_as': header['most_similar'],
                    'confidence': header['similarity_score'],
                    'context': header['context']
                })
                missing_sections.discard(header['most_similar'])
        
        return len(missing_sections) == 0, verified_headers

class ResearchPaperAnalyzer:
    def __init__(self):
        self.extractor = ExtractorAgent()
        self.verifier = VerifierAgent()

    def analyze_paper(self, pdf_path: str) -> Tuple[bool, List[Dict[str, str]]]:
        text = self.extractor.extract_text_from_pdf(pdf_path)
        if not text:
            return False, []
        
        headers = self.extractor.extract_headers(text)
        is_complete, verified_headers = self.verifier.verify_headers(headers)
        
        return is_complete, verified_headers

    def save_analysis(self, is_complete: bool, headers: List[Dict[str, str]], pdf_path: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "paper_analysis"
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_name = os.path.basename(pdf_path)
        output_file = os.path.join(output_dir, f"{pdf_name}_{timestamp}_analysis.json")
        
        analysis = {
            'is_complete': is_complete,
            'headers': headers,
            'timestamp': timestamp
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        
        return output_file

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
    is_complete, headers = analyzer.analyze_paper(args.pdf_path)
    
    if headers:
        output_file = analyzer.save_analysis(is_complete, headers, args.pdf_path)
        print(f"\nAnalysis saved to: {output_file}")
        print("\nFound headers:")
        for header in headers:
            print(f"- {header['original']} (verified as: {header['verified_as']}, confidence: {header['confidence']:.2f})")
        print(f"\nPaper structure is {'complete' if is_complete else 'incomplete'}")
    else:
        print("Failed to extract any headers from the paper")

if __name__ == "__main__":
    main() 