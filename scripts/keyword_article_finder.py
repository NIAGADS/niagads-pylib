import asyncio
import aiohttp
import pandas as pd
from metapub import PubMedFetcher
import os
import json
from datetime import datetime
import argparse
import random
import requests
from pathlib import Path
import urllib.parse
from enum import Enum
from typing import Optional, List, Dict, Any, Union

class FilterField(Enum):
    MESH_TERMS = "MeSH Terms"
    PUBLICATION_DATE = "Publication Date"
    OPEN_ACCESS = "Open Access"

class PubmedTrainingSetGenerator:
    def __init__(self, ncbi_api_key: Optional[str] = None):
        """Initialize the generator with optional API key"""
        self._ncbi_api_key = self._validate_api_key(ncbi_api_key)
        self._training_set = None
        self._filters = {}
        self._article_limit = 1000
        self._open_access_only = False
        self._pdf_output_dir = None
        self._fetch = PubMedFetcher(api_key=self._ncbi_api_key)

    def _validate_api_key(self, api_key: Optional[str]) -> str:
        """Validate and set the API key"""
        if api_key:
            return api_key
        elif "NCBI_API_KEY" in os.environ:
            return os.environ["NCBI_API_KEY"]
        else:
            print("Warning: No NCBI API key provided. Requests will be rate limited.")
            return ""

    def add_filter(self, field: FilterField, value: Any) -> None:
        """Add a filter to the search query"""
        self._filters[field] = value

    def set_limit(self, limit: int) -> None:
        """Set the maximum number of articles to return"""
        self._article_limit = limit

    def set_open_access_only(self, open_access_only: bool) -> None:
        """Set whether to only include open access articles"""
        self._open_access_only = open_access_only

    def set_pdf_output_dir(self, output_dir: str) -> None:
        """Set the directory where PDFs will be saved"""
        self._pdf_output_dir = os.path.abspath(output_dir)
        if not os.path.exists(self._pdf_output_dir):
            os.makedirs(self._pdf_output_dir)

    async def _download_pdf(self, pmid: str, pdf_url: str) -> Optional[str]:
        """Download a PDF for a given PMID"""
        try:
            safe_filename = f"PMID_{pmid}.pdf"
            output_path = os.path.join(self._pdf_output_dir, safe_filename)
            
            if os.path.exists(output_path):
                return output_path
                
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return output_path
        except Exception as e:
            print(f"Error downloading PDF for PMID {pmid}: {str(e)}")
            return None

    async def search_pubmed(self) -> Dict[str, Dict[str, Any]]:
        """Search PubMed with the configured filters"""
        if not self._filters.get(FilterField.MESH_TERMS):
            raise ValueError("At least one MeSH term must be provided")

        articles = {}

        mesh_terms = self._filters.get(FilterField.MESH_TERMS, [])
        if len(mesh_terms) > 5:
            raise ValueError("Maximum of 5 MeSH terms allowed")

        mesh_terms_query = " OR ".join([f'("{term}"[MeSH Terms])' for term in mesh_terms])
        
        year_filter = ""
        if FilterField.PUBLICATION_DATE in self._filters:
            year_start, year_end = self._filters[FilterField.PUBLICATION_DATE]
            if year_start and year_end:
                year_filter = f" AND ({year_start}:{year_end}[pdat])"

        open_access_filter = " AND (open access[filter])" if self._open_access_only else ""
        search_query = f'({mesh_terms_query}{year_filter}{open_access_filter})'

        print(f"Searching PubMed...")

        try:
            pmids = self._fetch.pmids_for_query(search_query, retmax=self._article_limit)

            for pmid in pmids:
                try:
                    article = self._fetch.article_by_pmid(pmid)
                    if article and not self._is_preprint(article.journal):
                        is_open_access = hasattr(article, 'open_access') and article.open_access
                        
                        if self._open_access_only and not is_open_access:
                            continue
                            
                        pdf_path = None
                        if is_open_access and hasattr(article, 'pdf_url') and article.pdf_url:
                            pdf_path = await self._download_pdf(pmid, article.pdf_url)
                            
                        if self._open_access_only and not pdf_path:
                            continue
                            
                        articles[pmid] = {
                            "pmid": pmid,
                            "title": article.title,
                            "abstract": article.abstract if hasattr(article, "abstract") else "",
                            "journal": article.journal,
                            "publication_date": article.pubdate,
                            "mesh_terms": article.mesh_terms if hasattr(article, "mesh_terms") else [],
                            "is_open_access": is_open_access,
                            "pdf_path": pdf_path
                        }
                except Exception as e:
                    print(f"Error fetching PMID {pmid}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error during PubMed search: {str(e)}")

        return articles

    def _is_preprint(self, journal: str) -> bool:
        """Check if a journal is a preprint"""
        journal_lower = journal.lower()
        preprint_keywords = {
            "medrxiv", "biorxiv", "arxiv", "preprint", "pre-print",
            "preprint server", "preprint repository", "preprint archive"
        }
        return any(keyword in journal_lower for keyword in preprint_keywords)

    def _filter_existing_articles(self, articles: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Filter out articles that already exist in the training set"""
        try:
            existing_pmids = set()
            if self._training_set:
                existing_pmids.update(self._training_set.keys())

            filtered_articles = {
                pmid: article 
                for pmid, article in articles.items() 
                if str(pmid) not in existing_pmids
            }

            print(f"Removed {len(articles) - len(filtered_articles)} existing articles")
            return filtered_articles

        except Exception as e:
            print(f"Error filtering existing articles: {str(e)}")
            return articles

    async def run(self) -> None:
        """Run the generator and save results to self._training_set"""
        articles = await self.search_pubmed()
        print(f"Found {len(articles)} articles after removing preprints")

        filtered_articles = self._filter_existing_articles(articles)
        print(f"Found {len(filtered_articles)} new articles")

        if filtered_articles:
            if self._training_set:
                self._training_set.update(filtered_articles)
            else:
                self._training_set = filtered_articles
            print(f"Added {len(filtered_articles)} new articles to training set")
        else:
            print("No new articles found")

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        """Return the training set as a dictionary"""
        return self._training_set or {}

    def as_json(self) -> str:
        """Return the training set as a JSON string"""
        return json.dumps(self._training_set or {}, indent=2)

    def save_to_file(self, filepath: str) -> None:
        """Save the training set to a file"""
        with open(filepath, 'w') as f:
            json.dump(self._training_set or {}, f, indent=2)

    def get_pubmed_ids(self) -> List[str]:
        """Get all PubMed IDs in the training set"""
        return list(self._training_set.keys()) if self._training_set else []

    def get_journals(self) -> List[str]:
        """Get all unique journals in the training set"""
        if not self._training_set:
            return []
        return list(set(article["journal"] for article in self._training_set.values()))

async def main(**kwargs):
    """Main function to run the generator from command line"""
    generator = PubmedTrainingSetGenerator(kwargs.get("ncbi_api_key"))
    
    if "mesh_terms" in kwargs:
        generator.add_filter(FilterField.MESH_TERMS, kwargs["mesh_terms"])
    
    if "year_start" in kwargs and "year_end" in kwargs:
        generator.add_filter(FilterField.PUBLICATION_DATE, (kwargs["year_start"], kwargs["year_end"]))
    
    if "open_access_only" in kwargs:
        generator.set_open_access_only(kwargs["open_access_only"])
    
    if "article_limit" in kwargs:
        generator.set_limit(kwargs["article_limit"])
    
    if "pdf_output_dir" in kwargs:
        generator.set_pdf_output_dir(kwargs["pdf_output_dir"])
    
    await generator.run()
    print(generator.as_json())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search PubMed for articles with MeSH terms")
    parser.add_argument("--mesh_terms", nargs="+", required=True, help="List of up to 5 MeSH terms to search for")
    parser.add_argument("--year_start", type=int, help="Start year for the search (optional)")
    parser.add_argument("--year_end", type=int, help="End year for the search (optional)")
    parser.add_argument("--ncbi_api_key", required=True, help="NCBI API key")
    parser.add_argument("--open_access_only", action="store_true", help="Only include open access articles")
    parser.add_argument("--article_limit", type=int, default=1000, help="Maximum number of articles to return")
    parser.add_argument("--pdf_output_dir", required=True, help="Full path to directory where PDFs will be saved")
    
    args = parser.parse_args()
    asyncio.run(main(**vars(args)))