import pandas as pd
from typing import Dict, Any, Optional, Tuple, Set
from .keyword_article_finder import PubmedTrainingSetGenerator, FilterField
import random
import argparse
import asyncio

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
                    search_query = f'({mesh_terms_query}{year_filter}{open_access_filter} AND {journal_query})'

                    print(f"Searching {journal} in {year} for {target_count} articles...")

                    try:
                        pmids = self._fetch.pmids_for_query(search_query, retmax=target_count * 8)

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
                                        
                                    target_journal_articles[journal].append({
                                        "pmid": pmid,
                                        "title": article.title,
                                        "abstract": article.abstract if hasattr(article, "abstract") else "",
                                        "journal": journal,
                                        "publication_date": article.pubdate,
                                        "mesh_terms": article.mesh_terms if hasattr(article, "mesh_terms") else [],
                                        "is_open_access": is_open_access,
                                        "pdf_path": pdf_path
                                    })
                            except Exception as e:
                                print(f"Error fetching PMID {pmid}: {str(e)}")
                                continue

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
    parser.add_argument("--mesh_terms", nargs="+", required=True, help="List of up to 5 MeSH terms to search for")
    parser.add_argument("--year_start", type=int, help="Start year for the search (optional)")
    parser.add_argument("--year_end", type=int, help="End year for the search (optional)")
    parser.add_argument("--ncbi_api_key", required=True, help="NCBI API key")
    parser.add_argument("--open_access_only", action="store_true", help="Only include open access articles")
    parser.add_argument("--article_limit", type=int, default=1000, help="Maximum number of articles to return")
    parser.add_argument("--pdf_output_dir", required=True, help="Full path to directory where PDFs will be saved")
    
    args = parser.parse_args()
    asyncio.run(main(**vars(args))) 