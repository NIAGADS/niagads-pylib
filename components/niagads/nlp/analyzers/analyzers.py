import random
from collections import Counter
from typing import Optional

import numpy as np
import plotly.graph_objects as go
from niagads.common.core import ComponentBaseMixin
from niagads.nlp.core import (
    STOPWORDS,
    NLPModel,
    NLPModelType,
    tokenize as _tokenize,
    validate_llm_type,
)
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering


class NgramPhrase(BaseModel):
    phrase: str
    count: int


class NgramPhraseCluster(BaseModel):
    label: str
    count: int
    members: list[NgramPhrase]


class PhraseClusterAnalyzer(ComponentBaseMixin):
    """
    Provides n-gram phrase extraction, semantic clustering, and word cloud plotting utilities.
    """

    def __init__(
        self,
        stopwords: set = STOPWORDS,
        model: Optional[NLPModel] = NLPModel.ALL_MINILM_L6_V2,
        use_embeddings: bool = True,
        top_n: int = 20,
        min_ngram: int = 1,
        max_ngram: int = 3,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__stopwords: set = stopwords
        self.__model: str = validate_llm_type(model, NLPModelType.EMBEDDING)
        self.__use_embeddings: bool = use_embeddings
        self.__top_n: int = top_n
        self.__min_ngram: int = min_ngram
        self.__max_ngram: int = max_ngram

    def tokenize(self, text: str | list[str]) -> list[str] | list[list[str]]:
        """
        Tokenize input text(s), lowercasing and removing stopwords and short tokens.
        Accepts a single string or a list of strings.
        Returns a list of tokens if input is a string, or a list of token lists if input is a list of strings.
        Raises TypeError if input is not a string or list of strings.
        """
        if not (
            isinstance(text, str)
            or (isinstance(text, list) and all(isinstance(t, str) for t in text))
        ):
            raise TypeError("text must be a string or a list of strings.")
        return _tokenize(text, self.__stopwords)

    def _count_ngram_candidates(
        self,
        tokens_list: list[list[str]],
    ) -> Counter:
        """
        Count all n-gram phrase candidates across all tokenized texts.
        Returns a Counter mapping phrase to count.
        """
        candidates = Counter()
        for tokens in tokens_list:
            n = len(tokens)
            for k in range(self.__min_ngram, min(self.__max_ngram, n) + 1):
                for i in range(n - k + 1):
                    phrase = " ".join(tokens[i : i + k])
                    candidates[phrase] += 1
        if not candidates:
            self.logger.warning("No n-gram candidates found in input tokens.")
        return candidates

    def _top_ngram_phrases(
        self,
        tokens_list: list[list[str]],
    ) -> list[NgramPhraseCluster]:
        """
        Return the top n most frequent n-gram phrases and their counts from the input token lists.
        Each result is a NgramPhraseCluster with a single member (the phrase and its count).
        """
        candidates = self._count_ngram_candidates(tokens_list)
        if not candidates:
            return []

        results = []
        for phrase, count in candidates.most_common(self.__top_n):
            member = NgramPhrase(phrase=phrase, count=count)
            cluster = NgramPhraseCluster(label=phrase, count=count, members=[member])
            results.append(cluster)
        return results

    def semantic_phrase_clustering(
        self,
        texts: list[str],
    ) -> list[NgramPhraseCluster]:
        """
        Analyze `texts` and return the top semantic patterns as a list of NgramPhraseCluster.

        This method generates candidate n-grams (after simple tokenization + stopword removal),
        counts frequencies, embeds unique candidate phrases, clusters them, and returns semantically grouped patterns.
        If clustering is not possible, it raises an error.

        If use_embeddings is False, the function skips semantic clustering and simply returns the top n most frequent n-gram phrases and their counts.

        Returns:
            list[NgramPhraseCluster]
        """

        # Tokenize input texts (lowercase, remove stopwords and short tokens)
        tokens_list = self.tokenize(texts)

        # If embeddings are not used, return top n-gram phrases by frequency only
        if not self.__use_embeddings:
            return self._top_ngram_phrases(tokens_list)

        # count n-gram candidates
        candidates = self._count_ngram_candidates(tokens_list)
        if not candidates:
            self.logger.warning("No n-gram candidates found for clustering.")
            return []

        # Get unique phrases sorted by frequency
        unique_phrases = [p for p, _ in candidates.most_common()]

        # Load the embedding model
        embedder = SentenceTransformer(self.__model)

        # Compute embeddings for all unique phrases
        embeddings = embedder.encode(
            unique_phrases, convert_to_numpy=True, show_progress_bar=False
        )

        # Determine number of clusters (at least 2, at most top_n, and not more than n_phrases)
        n_phrases = len(unique_phrases)
        n_clusters = min(max(2, n_phrases // 10), self.__top_n, n_phrases)
        if n_phrases <= 2 or n_clusters <= 1:
            self.logger.warning("Not enough unique phrases for clustering.")
            return []

        # Perform agglomerative clustering on phrase embeddings
        clustering = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clustering.fit_predict(embeddings)

        # Compute centroid for each cluster
        centroids = [np.mean(embeddings[labels == lbl], axis=0) for lbl in set(labels)]

        # Group phrases by cluster label
        cluster_map = {}
        for i, phrase in enumerate(unique_phrases):
            lbl = labels[i]
            cluster_map.setdefault(lbl, []).append(
                NgramPhrase(phrase=phrase, count=candidates[phrase])
            )

        # For each cluster, select a representative label and sort members by frequency
        results = []
        for idx, (lbl, members) in enumerate(cluster_map.items()):
            total = sum(m.count for m in members)
            centroid = centroids[idx]
            member_phrases = [m.phrase for m in members]

            # Re-embed members to compute distances to centroid
            member_embs = embedder.encode(
                member_phrases, convert_to_numpy=True, show_progress_bar=False
            )
            dists = np.linalg.norm(member_embs - centroid, axis=1)
            rep_idx = int(np.argmin(dists))  # Closest phrase to centroid
            label = members[rep_idx].phrase
            members_sorted = sorted(members, key=lambda x: x.count, reverse=True)
            results.append(
                NgramPhraseCluster(label=label, count=total, members=members_sorted)
            )

        # Sort clusters by total count and return top_n
        results = sorted(results, key=lambda r: r.count, reverse=True)[: self.__top_n]
        return results

    def plot_ngram_wordcloud(
        self,
        clusters: list[NgramPhraseCluster],
        max_words: int = 100,
        title: str = "N-gram Word Cloud",
        width: int = 800,
        height: int = 500,
    ):
        """
        Generate a word cloud from a list of NgramPhraseCluster objects using Plotly.
        Each phrase's size is proportional to its count.
        """
        # Flatten all phrases and counts from clusters
        phrases = []
        counts = []
        for cluster in clusters:
            for member in cluster.members:
                phrases.append(member.phrase)
                counts.append(member.count)
        # Limit to max_words most frequent
        if len(phrases) > max_words:
            sorted_items = sorted(
                zip(phrases, counts), key=lambda x: x[1], reverse=True
            )[:max_words]
            phrases, counts = zip(*sorted_items)
        # Generate random positions for each word
        random.seed(42)
        x = [random.uniform(0, 1) for _ in phrases]
        y = [random.uniform(0, 1) for _ in phrases]
        # Scale font size by count
        min_font, max_font = 12, 48
        min_count, max_count = min(counts), max(counts)

        def scale_font(count):
            if max_count == min_count:
                return (max_font + min_font) // 2
            return int(
                min_font
                + (count - min_count) / (max_count - min_count) * (max_font - min_font)
            )

        font_sizes = [scale_font(c) for c in counts]
        # Create scatter plot with text
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="text",
                text=phrases,
                textfont={"size": font_sizes},
                textposition="middle center",
                hovertext=[f"{p}: {c}" for p, c in zip(phrases, counts)],
                hoverinfo="text",
            )
        )
        fig.update_layout(
            title=title,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            width=width,
            height=height,
            plot_bgcolor="white",
        )
        fig.show()
