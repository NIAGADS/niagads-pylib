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

#### Basic PubMed Search (PubmedTrainingSetGenerator)

The base class for searching PubMed articles with various filters:

```python
from scripts.keyword_article_finder import PubmedTrainingSetGenerator, FilterField

# Initialize the generator
generator = PubmedTrainingSetGenerator(ncbi_api_key="your_api_key")

# Add filters
generator.add_filter(FilterField.MESH_TERMS, ["Alzheimer Disease", "Dementia"])
generator.add_filter(FilterField.PUBLICATION_DATE, (2010, 2023))

# Configure options
generator.set_open_access_only(True)
generator.set_limit(1000)
generator.set_pdf_output_dir("path/to/pdf/directory")

# Run the search
await generator.run()

# Get results
results = generator.as_dict()  # Get as dictionary
json_results = generator.as_json()  # Get as JSON string
```

Command line usage:
```bash
python scripts/keyword_article_finder.py --meshTerms "Alzheimer Disease" "Dementia" --yearStart 2010 --yearEnd 2023 --openAccessOnly --articleLimit 1000 --pdfOutputDir path/to/pdf/directory
```

#### Journal-Specific PubMed Search (JournalSpecificPubmedGenerator)

Advanced search that maintains journal and year distribution from a reference dataset:

```python
from scripts.journal_specific_pubmed_generator import JournalSpecificPubmedGenerator

# Initialize the generator
generator = JournalSpecificPubmedGenerator(ncbi_api_key="your_api_key")

# Add filters
generator.add_filter(FilterField.MESH_TERMS, ["Alzheimer Disease", "Dementia"])

# Configure options
generator.set_open_access_only(True)
generator.set_limit(1000)
generator.set_pdf_output_dir("path/to/pdf/directory")

# Run the search
await generator.run()

# Get results
results = generator.as_dict()
```

The JournalSpecificPubmedGenerator requires:
- `filtered_articles.csv`: Reference dataset with article information
- `year_journal_distribution.csv`: Distribution data for sampling

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
│   ├── pubmed_analyzer.py           # Analyze PubMed articles
│   ├── research_paper_analyzer.py   # Analyze PDF papers
│   ├── keyword_article_finder.py    # Base PubMed search functionality
│   ├── journal_specific_pubmed_generator.py  # Journal-specific search
│   └── split_dataset.py            # Split dataset into train/test
├── .env                            # Environment variables
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Key Features

### PubmedTrainingSetGenerator
- Flexible search with multiple filters (MeSH terms, publication date, open access)
- PDF downloading for open access articles
- Configurable article limits
- Preprint filtering
- JSON/dictionary output formats

### JournalSpecificPubmedGenerator
- Maintains journal and year distribution from reference dataset
- Journal-specific sampling
- Year-specific filtering
- Inherits all features from PubmedTrainingSetGenerator

## Dependencies

- Python 3.7+
- See `requirements.txt` for full list of Python packages
- Tesseract OCR (for PDF text extraction)
- Poppler (for PDF to image conversion)

## Notes

- The PubMed analyzers require an NCBI API key
- The research paper analyzer uses SapBERT for semantic analysis
- All output files are saved in the specified output directory
- Open access filtering requires PDF availability

## License

[Your License Here]
