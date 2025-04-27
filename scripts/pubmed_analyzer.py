import asyncio
import aiohttp
import pandas as pd
from metapub import PubMedFetcher
import os
import argparse
from typing import List, Dict, Any, Optional
from collections import Counter


class PubmedAnalyzer:
    def __init__(self, ncbi_api_key: Optional[str] = None):
        """Initialize the analyzer with optional API key"""
        self._ncbi_api_key = self._validate_api_key(ncbi_api_key)
        self._fetch = PubMedFetcher(api_key=self._ncbi_api_key)
        self._articles = []
        self._output_dir = None

    def _validate_api_key(self, api_key: Optional[str]) -> str:
        """Validate and set the API key"""
        if api_key:
            return api_key
        elif "NCBI_API_KEY" in os.environ:
            return os.environ["NCBI_API_KEY"]
        else:
            print("Warning: No NCBI API key provided. Requests will be rate limited.")
            return ""

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for analysis results"""
        self._output_dir = os.path.abspath(output_dir)
        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir)

    async def fetch_article_info(self, pubmed_ids: List[str]) -> None:
        """Fetch article information for a list of PubMed IDs"""
        self._articles = []
        for pmid in pubmed_ids:
            try:
                article = self._fetch.article_by_pmid(pmid)
                if article:
                    year = article.year if hasattr(article, 'year') else None
                    mesh_terms = article.mesh_terms if hasattr(article, 'mesh_terms') else []
                    self._articles.append({
                        "pmid": pmid,
                        "title": article.title,
                        "journal": article.journal,
                        "year": year,
                        "mesh_terms": mesh_terms
                    })
            except Exception as e:
                print(f"Error fetching PMID {pmid}: {str(e)}")

    def _filter_preprints(self) -> List[Dict[str, Any]]:
        """Filter out preprint articles"""
        return [
            article
            for article in self._articles
            if not any(x in article["journal"].lower() for x in ["medrxiv", "biorxiv"])
        ]

    def analyze_year_distribution(self) -> pd.DataFrame:
        """Analyze and save year distribution of articles"""
        filtered_articles = self._filter_preprints()
        df = pd.DataFrame(filtered_articles)
        
        if self._output_dir:
            output_path = os.path.join(self._output_dir, "filtered_articles.csv")
            df.to_csv(output_path, index=False)
            print(f"Saved {len(filtered_articles)} articles to {output_path}")
        
        return df

    def analyze_journal_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze and save year-journal distribution of articles"""
        year_counts = df["year"].value_counts().sort_index()
        total_articles = len(df)

        journal_dist = df.groupby(["year", "journal"]).size().unstack(fill_value=0)
        output_data = []

        for year in year_counts.index:
            year_data = {
                "year": year,
                "article_count": year_counts[year],
                "proportion": year_counts[year] / total_articles,
            }

            year_journals = journal_dist.loc[year]
            for journal in year_journals.index:
                year_data[f"journal_{journal}"] = year_journals[journal] / year_counts[year]

            output_data.append(year_data)

        output_df = pd.DataFrame(output_data)
        
        if self._output_dir:
            output_path = os.path.join(self._output_dir, "year_journal_distribution.csv")
            output_df.to_csv(output_path, index=False)
            print(f"Saved year and journal distribution analysis to {output_path}")
        
        return output_df

    def analyze_mesh_terms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze and save MeSH term distribution"""
        all_mesh_terms = []
        for terms in df["mesh_terms"]:
            all_mesh_terms.extend(terms)
        
        mesh_counts = Counter(all_mesh_terms)
        mesh_df = pd.DataFrame(
            list(mesh_counts.items()), 
            columns=["mesh_term", "frequency"]
        ).sort_values("frequency", ascending=False)
        
        if self._output_dir:
            output_path = os.path.join(self._output_dir, "mesh_term_distribution.csv")
            mesh_df.to_csv(output_path, index=False)
            print(f"Saved MeSH term distribution analysis to {output_path}")
        
        return mesh_df

    async def analyze(self, pubmed_ids: List[str]) -> None:
        """Run the complete analysis pipeline"""
        if not self._output_dir:
            raise ValueError("Output directory must be set before running analysis")

        print("Fetching article information...")
        await self.fetch_article_info(pubmed_ids)

        print("Analyzing year distribution...")
        df = self.analyze_year_distribution()

        print("Analyzing journal distribution...")
        self.analyze_journal_distribution(df)

        print("Analyzing MeSH terms...")
        self.analyze_mesh_terms(df)


async def main():
    parser = argparse.ArgumentParser(description="Analyze PubMed articles")
    parser.add_argument(
        "--input", required=True, help="Path to input CSV file containing PubMed IDs"
    )
    parser.add_argument(
        "--output", required=True, help="Path to output directory for results"
    )
    parser.add_argument(
        "--ncbi_api_key", help="NCBI API key (optional, can also use NCBI_API_KEY environment variable)"
    )
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input)
        pubmed_ids = df["PMID"].tolist()
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return

    analyzer = PubmedAnalyzer(args.ncbi_api_key)
    analyzer.set_output_dir(args.output)
    await analyzer.analyze(pubmed_ids)


if __name__ == "__main__":
    asyncio.run(main())