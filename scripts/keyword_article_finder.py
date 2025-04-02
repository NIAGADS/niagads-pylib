import asyncio
import aiohttp
import pandas as pd
from metapub import PubMedFetcher
import os
from datetime import datetime
import argparse

NCBI_API_KEY = "22b3c09ba6f71022526646140a1d67ee2508"
os.environ['NCBI_API_KEY'] = NCBI_API_KEY

fetch = PubMedFetcher()

PREPRINT_KEYWORDS = {'medrxiv', 'biorxiv', 'arxiv', 'preprint', 'pre-print', 'preprint server', 'preprint repository', 'preprint archive'}

NUMBER_TO_FETCH = 2000

def is_preprint(journal):
    journal_lower = journal.lower()
    return any(keyword in journal_lower for keyword in PREPRINT_KEYWORDS)

def has_alzheimer_term(article):
    title = article.title.lower() if article.title else ''
    abstract = article.abstract.lower() if hasattr(article, 'abstract') and article.abstract else ''
    return 'alzheimer' in title or 'alzheimer' in abstract

async def search_pubmed(keywords):
    articles = []
    
    search_terms = []
    for keyword in keywords:
        search_terms.append(f'("{keyword}"[Title/Abstract])')
    
    alzheimer_terms = '(("Alzheimer Disease"[MeSH Terms]) OR ("Alzheimer\'s Disease"[Title/Abstract]))'
    search_query = f'({alzheimer_terms} AND ({" OR ".join(search_terms)}))'
    
    print(f"Searching PubMed with query: {search_query}")
    
    try:
        pmids = fetch.pmids_for_query(search_query, retmax=NUMBER_TO_FETCH)
        
        print(f"Found {len(pmids)} articles. Fetching details...")
        
        for pmid in pmids:
            try:
                article = fetch.article_by_pmid(pmid)
                if article and not is_preprint(article.journal) and has_alzheimer_term(article):
                    articles.append({'pmid': pmid, 'title': article.title, 'abstract': article.abstract if hasattr(article, 'abstract') else '', 'journal': article.journal})
            except Exception as e:
                print(f"Error fetching PMID {pmid}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error during PubMed search: {str(e)}")
    
    return articles

def filter_existing_articles(articles, existing_articles_file):
    try:
        existing_df = pd.read_csv(existing_articles_file)
        existing_pmids = set(existing_df['pmid'].astype(str))
        
        filtered_articles = [article for article in articles if str(article['pmid']) not in existing_pmids]
        
        print(f"Removed {len(articles) - len(filtered_articles)} existing articles")
        return filtered_articles
        
    except Exception as e:
        print(f"Error filtering existing articles: {str(e)}")
        return articles

async def main():
    parser = argparse.ArgumentParser(description='Search PubMed for Alzheimer\'s articles with keywords')
    parser.add_argument('--keywords', default='alzheimer_keywords.csv', help='Path to CSV file containing keywords')
    parser.add_argument('--existing', default='filtered_articles.csv', help='Path to CSV file containing existing articles')
    args = parser.parse_args()

    try:
        keywords_df = pd.read_csv(args.keywords)
        keywords = keywords_df['keyword'].tolist()
    except Exception as e:
        print(f"Error reading keywords file: {str(e)}")
        return

    articles = await search_pubmed(keywords)
    print(f"Found {len(articles)} articles after removing preprints")
    
    filtered_articles = filter_existing_articles(articles, args.existing)
    print(f"Found {len(filtered_articles)} new articles")
    
    if filtered_articles:
        df = pd.DataFrame(filtered_articles)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'new_alzheimer_articles_{timestamp}.csv'
        df.to_csv(output_file, index=False)
        print(f"Saved {len(filtered_articles)} articles to {output_file}")
    else:
        print("No new articles found")

if __name__ == "__main__":
    asyncio.run(main()) 