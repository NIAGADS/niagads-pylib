import asyncio
import aiohttp
import pandas as pd
from metapub import PubMedFetcher
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter
import re
import os
import spacy
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

NCBI_API_KEY = os.environ["NCBI_API_KEY"]

if NCBI_API_KEY is None:
    raise ValueError(
        "NCBI_API_KEY environment variable is not set. Please set it to your NCBI API key."
    )

nltk.download("punkt")
nltk.download("stopwords")

fetch = PubMedFetcher()

print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

CORE_TERMS = [
    "alzheimer",
    "dementia",
    "amyloid",
    "tau",
    "cognitive",
    "memory",
    "neurodegenerative",
    "brain",
    "neural",
    "amyloid-beta",
    "apoe",
    "neurofibrillary",
    "plaques",
    "synapse",
    "hippocampus",
    "cerebral",
]  # Can play around with these


def get_word_embedding(word):
    return nlp(word).vector


def calculate_similarity(word, core_terms):
    word_embedding = get_word_embedding(word)
    similarities = []

    for term in core_terms:
        term_embedding = get_word_embedding(term)
        similarity = cosine_similarity([word_embedding], [term_embedding])[0][0]
        similarities.append(similarity)

    return max(similarities)


async def fetch_article_info(pubmed_ids):
    articles = []
    for pmid in pubmed_ids:
        try:
            article = fetch.article_by_pmid(pmid)
            if article:
                year = None
                if article.year:
                    year = article.year
                articles.append(
                    {
                        "pmid": pmid,
                        "title": article.title,
                        "journal": article.journal,
                        "year": year,
                    }
                )
        except Exception as e:
            print(f"Error fetching PMID {pmid}: {str(e)}")
    return articles


def filter_preprints(articles):
    return [
        article
        for article in articles
        if not any(x in article["journal"].lower() for x in ["medrxiv", "biorxiv"])
    ]


def extract_keywords(titles):
    all_words = []
    stop_words = set(stopwords.words("english"))

    for title in titles:
        words = word_tokenize(title.lower())
        words = [word for word in words if word.isalpha() and word not in stop_words]
        all_words.extend(words)

    word_counts = Counter(all_words)

    relevant_terms = {}
    print("Analyzing word relevance...")

    for word, count in word_counts.items():
        if len(word) > 2:
            similarity = calculate_similarity(word, CORE_TERMS)
            if similarity > 0.3:
                relevant_terms[word] = count

    return dict(sorted(relevant_terms.items(), key=lambda x: x[1], reverse=True))


def analyze_year_journal_distribution(articles):
    df = pd.DataFrame(articles)

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
    output_df.to_csv("year_journal_distribution.csv", index=False)
    print(
        "Saved year and journal distribution analysis to year_journal_distribution.csv"
    )

    return output_df


async def main():
    try:
        df = pd.read_csv("scripts/pubmed_ids.csv")
        pubmed_ids = df["PMID"].tolist()
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return

    print("Fetching article information...")
    articles = await fetch_article_info(pubmed_ids)

    filtered_articles = filter_preprints(articles)

    df_filtered = pd.DataFrame(filtered_articles)
    df_filtered.to_csv("filtered_articles.csv", index=False)
    print(f"Saved {len(filtered_articles)} articles to filtered_articles.csv")

    distribution_df = analyze_year_journal_distribution(filtered_articles)

    titles = [article["title"] for article in filtered_articles]
    keyword_counts = extract_keywords(titles)

    df_keywords = pd.DataFrame(
        list(keyword_counts.items()), columns=["keyword", "frequency"]
    )
    df_keywords.to_csv("alzheimer_keywords.csv", index=False)
    print("Saved keyword analysis to alzheimer_keywords.csv")


if __name__ == "__main__":
    asyncio.run(main())
