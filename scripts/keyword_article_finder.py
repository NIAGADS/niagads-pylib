import asyncio
import aiohttp
import pandas as pd
from metapub import PubMedFetcher
import os
from datetime import datetime
import argparse
import random

NCBI_API_KEY = os.environ["NCBI_API_KEY"]

if NCBI_API_KEY is None:
    raise ValueError(
        "NCBI_API_KEY environment variable is not set. Please set it to your NCBI API key."
    )

fetch = PubMedFetcher()

PREPRINT_KEYWORDS = {
    "medrxiv",
    "biorxiv",
    "arxiv",
    "preprint",
    "pre-print",
    "preprint server",
    "preprint repository",
    "preprint archive",
}

NUMBER_TO_FETCH = 1000


def is_preprint(journal):
    journal_lower = journal.lower()
    return any(keyword in journal_lower for keyword in PREPRINT_KEYWORDS)


def has_alzheimer_term(article):
    title = article.title.lower() if article.title else ""
    abstract = (
        article.abstract.lower()
        if hasattr(article, "abstract") and article.abstract
        else ""
    )
    return "alzheimer" in title or "alzheimer" in abstract


def get_year_range_and_journals():
    try:
        df = pd.read_csv("filtered_articles.csv")
        min_year = df["year"].min()
        max_year = df["year"].max()
        journals = set(df["journal"].unique())
        return min_year, max_year, journals
    except Exception as e:
        print(f"Error reading filtered_articles.csv: {str(e)}")
        return None, None, set()


def load_distribution_data():
    try:
        df = pd.read_csv("year_journal_distribution.csv")
        return df
    except Exception as e:
        print(f"Error reading distribution data: {str(e)}")
        return None


def get_target_distribution(total_articles):
    distribution_df = load_distribution_data()
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


async def search_pubmed(keywords):
    articles = []

    min_year, max_year, target_journals = get_year_range_and_journals()

    year_distribution, distribution_df = get_target_distribution(NUMBER_TO_FETCH)
    if year_distribution is None:
        print("Could not load distribution data, falling back to default search")
        return await default_search(keywords)

    search_terms = []
    for keyword in keywords:
        search_terms.append(f'("{keyword}"[Title/Abstract])')

    alzheimer_terms = '(("Alzheimer Disease"[MeSH Terms]) OR ("Alzheimer\'s Disease"[Title/Abstract]))'

    print(f"Searching PubMed with journal-specific sampling...")

    try:
        for year, year_data in year_distribution.items():
            if year_data["target_count"] == 0:
                continue

            year_filter = f" AND ({year}[pdat])"
            print(f"\nProcessing year {year}...")

            target_journal_articles = {
                journal: [] for journal in year_data["journal_proportions"].keys()
            }

            for journal, proportion in year_data["journal_proportions"].items():
                target_count = int(proportion * year_data["target_count"])
                if target_count == 0:
                    continue

                journal_query = f'("{journal}"[Journal])'
                search_query = f'({alzheimer_terms} AND ({" OR ".join(search_terms)}){year_filter} AND {journal_query})'

                print(f"Searching {journal} in {year} for {target_count} articles...")

                try:
                    pmids = fetch.pmids_for_query(search_query, retmax=target_count * 8)

                    for pmid in pmids:
                        try:
                            article = fetch.article_by_pmid(pmid)
                            if (
                                article
                                and not is_preprint(article.journal)
                                and has_alzheimer_term(article)
                            ):
                                target_journal_articles[journal].append(
                                    {
                                        "pmid": pmid,
                                        "title": article.title,
                                        "abstract": (
                                            article.abstract
                                            if hasattr(article, "abstract")
                                            else ""
                                        ),
                                        "journal": journal,
                                        "year": year,
                                    }
                                )
                        except Exception as e:
                            print(f"Error fetching PMID {pmid}: {str(e)}")
                            continue

                    print(
                        f"Found {len(target_journal_articles[journal])} articles for {journal}"
                    )

                except Exception as e:
                    print(
                        f"Error during PubMed search for {journal} in {year}: {str(e)}"
                    )

            for journal, journal_articles in target_journal_articles.items():
                target_count = int(
                    year_data["journal_proportions"][journal]
                    * year_data["target_count"]
                )

                if len(journal_articles) < target_count:
                    print(
                        f"Warning: Only found {len(journal_articles)} articles for {journal} in {year}, but needed {target_count}"
                    )
                    articles.extend(journal_articles)
                else:
                    selected_articles = random.sample(journal_articles, target_count)
                    articles.extend(selected_articles)

            print(f"\nYear {year} summary:")
            for journal, journal_articles in target_journal_articles.items():
                target_count = int(
                    year_data["journal_proportions"][journal]
                    * year_data["target_count"]
                )
                print(
                    f"  - {journal}: Found {len(journal_articles)}, Selected {min(target_count, len(journal_articles))}"
                )

    except Exception as e:
        print(f"Error during PubMed search: {str(e)}")

    return articles


async def default_search(keywords):
    articles = []
    search_terms = []
    for keyword in keywords:
        search_terms.append(f'("{keyword}"[Title/Abstract])')

    alzheimer_terms = '(("Alzheimer Disease"[MeSH Terms]) OR ("Alzheimer\'s Disease"[Title/Abstract]))'
    search_query = f'({alzheimer_terms} AND ({" OR ".join(search_terms)}))'

    try:
        pmids = fetch.pmids_for_query(search_query, retmax=NUMBER_TO_FETCH)

        for pmid in pmids:
            try:
                article = fetch.article_by_pmid(pmid)
                if (
                    article
                    and not is_preprint(article.journal)
                    and has_alzheimer_term(article)
                ):
                    articles.append(
                        {
                            "pmid": pmid,
                            "title": article.title,
                            "abstract": (
                                article.abstract if hasattr(article, "abstract") else ""
                            ),
                            "journal": article.journal,
                            "year": article.year,
                        }
                    )
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
            df_new = pd.read_csv("new_alzheimer_articles.csv")
            existing_pmids.update(df_new["pmid"].astype(str))
        except FileNotFoundError:
            pass

        try:
            df_filtered = pd.read_csv("filtered_articles.csv")
            existing_pmids.update(df_filtered["pmid"].astype(str))
        except FileNotFoundError:
            pass

        filtered_articles = [
            article
            for article in articles
            if str(article["pmid"]) not in existing_pmids
        ]

        print(f"Removed {len(articles) - len(filtered_articles)} existing articles")
        return filtered_articles

    except Exception as e:
        print(f"Error filtering existing articles: {str(e)}")
        return articles


async def main():
    parser = argparse.ArgumentParser(
        description="Search PubMed for Alzheimer's articles with keywords"
    )
    parser.add_argument(
        "--keywords",
        default="alzheimer_keywords.csv",
        help="Path to CSV file containing keywords",
    )
    args = parser.parse_args()

    try:
        keywords_df = pd.read_csv(args.keywords)
        keywords = keywords_df["keyword"].tolist()
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
            df_existing = pd.read_csv("new_alzheimer_articles.csv")
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv("new_alzheimer_articles.csv", index=False)
            print(
                f"Added {len(filtered_articles)} new articles to new_alzheimer_articles.csv"
            )
        except FileNotFoundError:
            df_new.to_csv("new_alzheimer_articles.csv", index=False)
            print(
                f"Created new_alzheimer_articles.csv with {len(filtered_articles)} articles"
            )
    else:
        print("No new articles found")


if __name__ == "__main__":
    asyncio.run(main())
