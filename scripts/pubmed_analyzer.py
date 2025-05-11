import asyncio
import aiohttp
import pandas as pd
from metapub import PubMedFetcher
import os
import argparse
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime


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

    def _validate_input_file(self, input_path: str) -> str:
        """Validate input file path and format"""
        if not os.path.exists(input_path):
            raise ValueError(f"Input file does not exist: {input_path}")
        if not input_path.lower().endswith('.csv'):
            raise ValueError("Input file must be a CSV file")
        return input_path

    def _validate_pubmed_ids(self, pubmed_ids: List[Any]) -> None:
        """Validate PubMed IDs"""
        if not pubmed_ids:
            raise ValueError("No PubMed IDs provided")
        if not all(isinstance(pmid, (int, str)) and str(pmid).isdigit() for pmid in pubmed_ids):
            raise ValueError("All PMIDs must be valid numeric identifiers")

    def _validate_csv_content(self, df: pd.DataFrame) -> None:
        """Validate CSV content"""
        if "PMID" not in df.columns:
            raise ValueError("Input CSV must contain a 'PMID' column")

    def _validate_and_convert_path(self, path: str) -> str:
        """Validate and convert a path to absolute path if needed"""
        try:
            if os.path.isabs(path):
                abs_path = path
            else:
                abs_path = os.path.abspath(path)
                
            os.makedirs(abs_path, exist_ok=True)
            return abs_path
        except Exception:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_dir = os.path.abspath(f"output_{timestamp}")
            os.makedirs(default_dir, exist_ok=True)
            print(f"Warning: Invalid output directory provided. Using default directory: {default_dir}")
            return default_dir

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for analysis results"""
        self._output_dir = self._validate_and_convert_path(output_dir)

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
        "--output", help="Path to output directory for results (optional, defaults to timestamped directory in working directory)"
    )
    parser.add_argument(
        "--ncbiApiKey", help="NCBI API key (optional, can also use NCBI_API_KEY environment variable)"
    )
    args = parser.parse_args()

    try:
        analyzer = PubmedAnalyzer(args.ncbiApiKey)
        
        input_path = analyzer._validate_and_convert_path(args.input)
        input_path = analyzer._validate_input_file(input_path)
        
        output_path = analyzer._validate_and_convert_path(args.output) if args.output else analyzer._validate_and_convert_path("")
        
        df = pd.read_csv(input_path)
        analyzer._validate_csv_content(df)
        
        pubmed_ids = df["PMID"].tolist()
        analyzer._validate_pubmed_ids(pubmed_ids)
        
        analyzer.set_output_dir(output_path)
        await analyzer.analyze(pubmed_ids)
        
    except ValueError as e:
        print(f"Error: {str(e)}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())