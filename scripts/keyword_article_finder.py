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

def get_year_range_and_journals():
    try:
        df = pd.read_csv('filtered_articles.csv')
        min_year = df['year'].min()
        max_year = df['year'].max()
        journals = set(df['journal'].unique())
        return min_year, max_year, journals
    except Exception as e:
        print(f"Error reading filtered_articles.csv: {str(e)}")
        return None, None, set()

async def search_pubmed(keywords):
    articles = []
    
    # Get year range and journals from filtered articles
    min_year, max_year, target_journals = get_year_range_and_journals()
    
    search_terms = []
    for keyword in keywords:
        search_terms.append(f'("{keyword}"[Title/Abstract])')
    
    alzheimer_terms = '(("Alzheimer Disease"[MeSH Terms]) OR ("Alzheimer\'s Disease"[Title/Abstract]))'
    
    # Add year range to search query if available
    year_filter = ""
    if min_year and max_year:
        year_filter = f' AND ({min_year}:{max_year}[pdat])'
    
    search_query = f'({alzheimer_terms} AND ({" OR ".join(search_terms)}){year_filter})'
    
    print(f"Searching PubMed with query: {search_query}")
    
    try:
        pmids = fetch.pmids_for_query(search_query, retmax=NUMBER_TO_FETCH)
        
        print(f"Found {len(pmids)} articles. Fetching details...")
        
        for pmid in pmids:
            try:
                article = fetch.article_by_pmid(pmid)
                if article and not is_preprint(article.journal) and has_alzheimer_term(article):
                    # Check if article is from one of the target journals
                    if target_journals and article.journal not in target_journals:
                        continue
                        
                    # Get publication year
                    year = None
                    if article.publication_date:
                        year = article.publication_date.year
                    
                    articles.append({
                        'pmid': pmid, 
                        'title': article.title, 
                        'abstract': article.abstract if hasattr(article, 'abstract') else '', 
                        'journal': article.journal,
                        'year': year
                    })
            except Exception as e:
                print(f"Error fetching PMID {pmid}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error during PubMed search: {str(e)}")
    
    return articles

def filter_existing_articles(articles):
    try:
        existing_pmids = set()
        
        try:
            df_new = pd.read_csv('new_alzheimer_articles.csv')
            existing_pmids.update(df_new['pmid'].astype(str))
        except FileNotFoundError:
            pass
            
        try:
            df_filtered = pd.read_csv('filtered_articles.csv')
            existing_pmids.update(df_filtered['pmid'].astype(str))
        except FileNotFoundError:
            pass
        
        filtered_articles = [article for article in articles if str(article['pmid']) not in existing_pmids]
        
        print(f"Removed {len(articles) - len(filtered_articles)} existing articles")
        return filtered_articles
        
    except Exception as e:
        print(f"Error filtering existing articles: {str(e)}")
        return articles

async def main():
    parser = argparse.ArgumentParser(description='Search PubMed for Alzheimer\'s articles with keywords')
    parser.add_argument('--keywords', default='alzheimer_keywords.csv', help='Path to CSV file containing keywords')
    args = parser.parse_args()

    try:
        keywords_df = pd.read_csv(args.keywords)
        keywords = keywords_df['keyword'].tolist()
    except Exception as e:
        print(f"Error reading keywords file: {str(e)}")
        return

    articles = await search_pubmed(keywords)
    print(f"Found {len(articles)} articles after removing preprints")
    
    filtered_articles = filter_existing_articles(articles)
    print(f"Found {len(filtered_articles)} new articles")
    
    if filtered_articles:
        df_new = pd.DataFrame(filtered_articles)
        try:
            df_existing = pd.read_csv('new_alzheimer_articles.csv')
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv('new_alzheimer_articles.csv', index=False)
            print(f"Added {len(filtered_articles)} new articles to new_alzheimer_articles.csv")
        except FileNotFoundError:
            df_new.to_csv('new_alzheimer_articles.csv', index=False)
            print(f"Created new_alzheimer_articles.csv with {len(filtered_articles)} articles")
    else:
        print("No new articles found")

if __name__ == "__main__":
    asyncio.run(main()) 