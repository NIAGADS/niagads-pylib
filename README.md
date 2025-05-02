# AI Bibliography Analysis

This project provides tools for analyzing research papers and PubMed articles using AI. It includes functionality for extracting and analyzing paper sections, finding relevant articles, and analyzing bibliographic data.

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-bibliography-analysis
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Create a `.env` file in the project root
   - Add your NCBI API key:
   ```
   NCBI_API_KEY=your_api_key_here
   ```
   - You can get an API key from [NCBI](https://www.ncbi.nlm.nih.gov/account/)

5. Download required models:
```bash
python -m spacy download en_core_web_md
```

## Usage

### 1. PubMed Article Analysis

Analyze a collection of PubMed articles:

```bash
python scripts/pubmed_analyzer.py --input path/to/pubmed_ids.csv --output path/to/output/directory
```

Arguments:
- `--input`: Path to CSV file containing PubMed IDs (must have a 'PMID' column)
- `--output`: Directory where results will be saved

Output files:
- `filtered_articles.csv`: Articles after preprocessing
- `alzheimer_keywords.csv`: Extracted keywords and their frequencies
- `year_journal_distribution.csv`: Distribution analysis

### 2. Research Paper Analysis

Analyze a single research paper PDF:

```bash
python scripts/research_paper_analyzer.py path/to/paper.pdf
```

Output:
- JSON file containing:
  - Paper structure completeness
  - Extracted headers with confidence scores
  - Context for each section

### 3. Keyword Article Finder

Find articles based on keywords:

```bash
python scripts/keyword_article_finder.py --keywords path/to/keywords.csv
```

Arguments:
- `--keywords`: Path to CSV file containing keywords (must have a 'keyword' column)

## Project Structure

```
ai-bibliography-analysis/
├── scripts/
│   ├── pubmed_analyzer.py      # Analyze PubMed articles
│   ├── research_paper_analyzer.py  # Analyze PDF papers
│   ├── keyword_article_finder.py   # Find articles by keywords
│   └── split_dataset.py        # Split dataset into train/test
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Dependencies

- Python 3.7+
- See `requirements.txt` for full list of Python packages
- Tesseract OCR (for PDF text extraction)
- Poppler (for PDF to image conversion)

## Notes

- The PubMed analyzer requires an NCBI API key
- The research paper analyzer uses SapBERT for semantic analysis
- All output files are saved in the specified output directory
- The code uses environment variables for sensitive data

## License

[Your License Here]
