# PubMed Article Analyzer

This project analyzes PubMed articles to extract and analyze information about Alzheimer's Disease research. It includes tools for filtering articles, analyzing keywords, and splitting datasets for machine learning purposes.

## Project Structure

```
.
├── scripts/                    # Python scripts
│   ├── pubmed_analyzer.py      # Main PubMed article analysis script
│   ├── keyword_article_finder.py # Keyword analysis and article finding
│   ├── split_dataset.py        # Dataset splitting utility
│   ├── research_paper_analyzer.py # AI-powered research paper analysis
│   └── pubmed_ids.csv          # Input PubMed IDs
├── requirements.txt            # Python dependencies
└── output files               # Generated analysis results
```

## Requirements

- Python 3.12+
- Tesseract OCR (for PDF text extraction)
- Required packages:
  - metapub==0.5.7
  - aiohttp>=3.9.3
  - pandas==2.1.4
  - nltk==3.8.1
  - scikit-learn==1.4.0
  - numpy==1.26.3
  - spacy>=3.7.3
  - transformers>=4.30.0
  - torch>=2.0.0
  - sentence-transformers>=2.2.2
  - pytesseract>=0.3.10
  - pdf2image>=1.16.3

## Installation

1. Clone the repository
2. Install Tesseract OCR:
   - Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`
3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Prepare your input data:
   - Place your PubMed IDs in `scripts/pubmed_ids.csv` with a column named 'pmid'
   - For PDF analysis, provide the path to your research paper PDF

2. Run the analysis scripts:
```bash
# Analyze PubMed articles
python scripts/pubmed_analyzer.py

# Find articles based on keywords
python scripts/keyword_article_finder.py

# Split dataset into train/test sets (optional)
python scripts/split_dataset.py

# Analyze a research paper PDF
python scripts/research_paper_analyzer.py path/to/your/paper.pdf
```

## Features

### Research Paper Analyzer
The enhanced research paper analyzer uses AI and machine learning to:
- Extract text from PDFs using both PyPDF2 and OCR
- Identify results/findings sections using semantic analysis
- Verify section content using transformer models
- Generate high-quality summaries using BART model
- Save summaries with timestamps for reference

Key AI/ML components:
- Sentence Transformers for semantic similarity
- DistilBERT for section classification
- BART model for summarization
- Multi-metric quality scoring system

### Output Files

The scripts generate several CSV files:

1. `filtered_articles.csv`: Contains article information of PubMed research with NIAGADS reference
   - Columns: pmid, title, journal, year

2. `alzheimer_keywords.csv`: Contains frequency analysis of Alzheimer's Disease related keywords
   - Columns: keyword, frequency

3. `new_alzheimer_articles.csv`: Contains article information of PubMed research related to Alzheimer's Disease without NIAGADS reference
   - Columns: pmid, title, abstract, journal, year

4. `alzheimer_articles_train.csv` and `alzheimer_articles_test.csv`: Split datasets for machine learning (if using split_dataset.py)
   - Contains a subset of the articles split into training and testing sets
   - Columns: pmid, title, abstract, journal, year

5. Paper summaries: Generated in the `paper_summaries` directory
   - Format: `{pdf_name}_{timestamp}_summary.txt`
   - Contains AI-generated summaries of research paper findings

## License

This project is licensed under the terms included in the LICENSE file.
