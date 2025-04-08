# PubMed Article Analyzer

This project analyzes PubMed articles to extract and analyze information about Alzheimer's Disease research. It includes tools for filtering articles, analyzing keywords, and splitting datasets for machine learning purposes.

## Project Structure

```
.
├── scripts/                    # Python scripts
│   ├── pubmed_analyzer.py      # Main PubMed article analysis script
│   ├── keyword_article_finder.py # Keyword analysis and article finding
│   ├── split_dataset.py        # Dataset splitting utility
│   └── pubmed_ids.csv          # Input PubMed IDs
├── requirements.txt            # Python dependencies
└── output files               # Generated analysis results
```

## Requirements

- Python 3.7+
- Required packages:
  - metapub==0.5.7
  - aiohttp>=3.9.3
  - pandas==2.1.4
  - nltk==3.8.1
  - scikit-learn==1.4.0
  - numpy==1.26.3
  - spacy>=3.7.3

## Installation

1. Clone the repository
2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Prepare your input data:
   - Place your PubMed IDs in `scripts/pubmed_ids.csv` with a column named 'pmid'

2. Run the analysis scripts:
```bash
# Analyze PubMed articles
python scripts/pubmed_analyzer.py

# Find articles based on keywords
python scripts/keyword_article_finder.py

# Split dataset into train/test sets (optional)
python scripts/split_dataset.py
```

## Output Files

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

## License

This project is licensed under the terms included in the LICENSE file.
