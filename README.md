# PubMed Article Analyzer

These scripts analyze PubMed articles to extract information about Alzheimer's Disease research.

## Requirements

- Python 3.7+
- Required packages listed in `requirements.txt`

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Prepare your input CSV file named `pubmed_ids.csv` with a column named 'pmid' containing PubMed IDs on the first column.

2. Run the script:
```bash
python pubmed_analyzer.py
```

3. Run the script:
```bash
python keyword_article_finder.py
```

## Output

The scripts will generate three CSV files:

1. `filtered_articles.csv`: Contains article information of PubMed research with NIAGADS reference
   - Columns: pmid, title, journal

2. `alzheimer_keywords.csv`: Contains frequency analysis of Alzheimer's Disease related keywords
   - Columns: keyword, frequency

3. `new_alzheimer_articles.csv`: Contains article information of PubMed research related to Alzheimer's Disease without NIAGADS reference
   - Columns: pmid, title, abstract, journal
