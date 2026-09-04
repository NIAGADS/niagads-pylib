"""Typing utilities for embedding functions."""

from typing import Protocol

Embedding = list[float]
EmbeddingBatch = list[Embedding]


class EmbeddingFunction(Protocol):
    """Protocol for asynchronous batch embedding functions.

    An embedding function accepts a list of text phrases and returns one
    embedding vector for each input phrase, preserving input order.

    NOTE: must be able to calculate batch embeddings

    Example:
        async def embed_texts(phrases: list[str]) -> EmbeddingBatch:
            return [[0.1, 0.2], [0.3, 0.4]]

        embedding_function(embed_texts)

    """

    async def __call__(
        self,
        phrases: list[str],
    ) -> EmbeddingBatch:
        """Generate embeddings for a batch of text phrases.

        Args:
            phrases (list[str]): Text phrases to embed.

        Returns:
            Embedding vectors corresponding to the input phrases, in the
            same order.

        """
        ...


def embedding_function(
    func: EmbeddingFunction,
) -> EmbeddingFunction:
    """Mark and type-check a function as an embedding function.

    This decorator provides an explicit indication that a function is
    intended to satisfy the :class:`EmbeddingFunction` protocol. Static
    type checkers can verify that the decorated function has a compatible
    signature.

    Args:
        func: Asynchronous batch embedding function.

    Returns:
        The original function, typed as an :class:`EmbeddingFunction`.

    Example:
        @embedding_function
        async def embed_texts(phrases: list[str]) -> EmbeddingBatch:
            return [
                [0.1, 0.2, 0.3]
                for _ in phrases
            ]

        embeddings = await embed_texts(
            ["microglia", "Alzheimer disease"]
        )

    """
    return func
