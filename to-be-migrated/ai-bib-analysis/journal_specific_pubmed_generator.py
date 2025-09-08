import pandas as pd
from typing import Dict, Any, Optional, Tuple, Set, List
from .keyword_article_finder import PubmedTrainingSetGenerator, FilterField
import random
import argparse
import asyncio
import os
from datetime import datetime

class JournalSpecificPubmedGenerator(PubmedTrainingSetGenerator):
    def __init__(self, ncbi_api_key: Optional[str] = None):
        """Initialize the generator with optional API key"""
        super().__init__(ncbi_api_key)
        self._year_distribution = None
        self._target_journals: Set[str] = set()

    def _get_year_range_and_journals(self) -> Tuple[Optional[int], Optional[int], Set[str]]:
        """Get year range and target journals from filtered_articles.csv"""
        try:
            df = pd.read_csv("filtered_articles.csv")
            min_year = df["year"].min()
            max_year = df["year"].max()
            journals = set(df["journal"].unique())
            return min_year, max_year, journals
        except Exception as e:
            print(f"Error reading filtered_articles.csv: {str(e)}")
            return None, None, set()

    def _load_distribution_data(self) -> Optional[pd.DataFrame]:
        """Load year and journal distribution data"""
        try:
            return pd.read_csv("year_journal_distribution.csv")
        except Exception as e:
            print(f"Error reading distribution data: {str(e)}")
            return None

    def _get_target_distribution(self, total_articles: int) -> Tuple[Optional[Dict], Optional[pd.DataFrame]]:
        """Calculate target distribution of articles by year and journal"""
        distribution_df = self._load_distribution_data()
        if distribution_df is None:
            return None, None

        year_distribution = {}
        for _, row in distribution_df.iterrows():
            year_distribution[int(row["year"])] = {
                "target_count": int(row["proportion"] * total_articles),
                "journal_proportions": {
                    col.replace("journal_", ""): val
                    for col, val in row.items()
                    if col.startswith("journal_") and val > 0
                },
            }

        return year_distribution, distribution_df

    async def search_pubmed(self) -> Dict[str, Dict[str, Any]]:
        """Search PubMed with journal-specific sampling"""
        if not self._filters.get(FilterField.MESH_TERMS):
            raise ValueError("At least one MeSH term must be provided")

        articles = {}
        min_year, max_year, self._target_journals = self._get_year_range_and_journals()
        self._year_distribution, _ = self._get_target_distribution(self._article_limit)

        if self._year_distribution is None:
            print("Could not load distribution data, falling back to default search")
            return await super().search_pubmed()

        print(f"Searching PubMed with journal-specific sampling...")

        try:
            for year, year_data in self._year_distribution.items():
                if year_data["target_count"] == 0:
                    continue

                print(f"\nProcessing year {year}...")

                target_journal_articles = {
                    journal: [] for journal in year_data["journal_proportions"].keys()
                }

                for journal, proportion in year_data["journal_proportions"].items():
                    target_count = int(proportion * year_data["target_count"])
                    if target_count == 0:
                        continue

                    journal_query = f'("{journal}"[Journal])'
                    search_query = self._build_search_query(f" AND {journal_query}", year=year)
                    print(f"Searching {journal} in {year} for {target_count} articles...")

                    try:
                        journal_articles = await self._fetch_and_process_articles(search_query, target_count * 8)
                        target_journal_articles[journal] = list(journal_articles.values())
                        print(f"Found {len(target_journal_articles[journal])} articles for {journal}")

                    except Exception as e:
                        print(f"Error during PubMed search for {journal} in {year}: {str(e)}")

                for journal, journal_articles in target_journal_articles.items():
                    target_count = int(year_data["journal_proportions"][journal] * year_data["target_count"])

                    if len(journal_articles) < target_count:
                        print(f"Warning: Only found {len(journal_articles)} articles for {journal} in {year}, but needed {target_count}")
                        for article in journal_articles:
                            articles[article["pmid"]] = article
                    else:
                        selected_articles = random.sample(journal_articles, target_count)
                        for article in selected_articles:
                            articles[article["pmid"]] = article

                print(f"\nYear {year} summary:")
                for journal, journal_articles in target_journal_articles.items():
                    target_count = int(year_data["journal_proportions"][journal] * year_data["target_count"])
                    print(f"  - {journal}: Found {len(journal_articles)}, Selected {min(target_count, len(journal_articles))}")

        except Exception as e:
            print(f"Error during PubMed search: {str(e)}")

        return articles

async def main(**kwargs):
    """Main function to run the generator from command line"""
    generator = JournalSpecificPubmedGenerator(kwargs.get("ncbi_api_key"))
    
    if "mesh_terms" in kwargs:
        if len(kwargs["mesh_terms"]) > 5:
            raise ValueError("Maximum of 5 MeSH terms allowed")
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
    parser = argparse.ArgumentParser(description="Search PubMed for articles with MeSH terms using journal-specific sampling")
    parser.add_argument("--meshTerms", nargs="+", required=True, help="List of up to 5 MeSH terms to search for")
    parser.add_argument("--yearStart", type=int, help="Start year for the search (optional)")
    parser.add_argument("--yearEnd", type=int, help="End year for the search (optional)")
    parser.add_argument("--ncbiApiKey", help="NCBI API key (optional, can also use NCBI_API_KEY environment variable)")
    parser.add_argument("--openAccessOnly", action="store_true", help="Only include open access articles")
    parser.add_argument("--articleLimit", type=int, default=1000, help="Maximum number of articles to return")
    parser.add_argument("--pdfOutputDir", help="Directory where PDFs will be saved (optional, defaults to timestamped directory in working directory)")
    
    args = parser.parse_args()
    
    kwargs = {
        "mesh_terms": args.meshTerms,
        "year_start": args.yearStart,
        "year_end": args.yearEnd,
        "ncbi_api_key": args.ncbiApiKey,
        "open_access_only": args.openAccessOnly,
        "article_limit": args.articleLimit,
        "pdf_output_dir": args.pdfOutputDir
    }
    
    try:
        asyncio.run(main(**kwargs))
    except ValueError as e:
        print(f"Error: {str(e)}")
        exit(1) 