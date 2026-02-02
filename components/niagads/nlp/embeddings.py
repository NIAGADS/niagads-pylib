from functools import lru_cache
from hashlib import sha256

from niagads.nlp.llm_types import LLM, NLPModelType
from sentence_transformers import SentenceTransformer


class TextEmbeddingGenerator:
    """Calculate and cache text embeddings using SentenceTransformer."""

    def __init__(self, model: LLM = LLM.ALL_MINILM_L6_V2):
        self.__model = self.__initialize_model(model)

    @staticmethod
    @lru_cache(maxsize=1)
    def __initialize_model(model: LLM) -> SentenceTransformer:
        """
        Get or load a cached SentenceTransformer model.

        Args:
            model (LLM): The embedding model to load.

        Returns:
            SentenceTransformer: The loaded model instance (cached).
        """
        LLM.validate(model, NLPModelType.EMBEDDING)
        return SentenceTransformer(str(model))

    @staticmethod
    def list_registered_models(self):
        return LLM.list(NLPModelType.EMBEDDING)

    def generate(
        self,
        text: str,
        normalize: bool = True,
        as_list: bool = True,
    ) -> list[float]:
        """
        Calculate a text embedding using SentenceTransformer.

        Args:
            text (str): The input text to embed.
            normalize (bool): Whether to normalize the embedding to unit length. Defaults to True.
                Set to True for cosine similarity operations (e.g., pgvector cosine_distance),
                as normalized vectors ensure fair comparison regardless of text length and enable
                efficient distance computation. Set to False only when using Euclidean distance
                or when magnitude carries semantic meaning.
            as_list (bool): Whether to return the embedding as a Python list. Defaults to True.
                Set to True for database storage and JSON serialization. Set to False to return
                the raw NumPy array for performance-critical operations.

        Returns:
            list[float] or numpy array: The embedding vector as a list of floats (if as_list=True)
                or as a NumPy array (if as_list=False).

        Raises:
            ValueError: If the model is not a valid embedding model.
        """

        embedding = self.__model.encode(text, normalize_embeddings=normalize)
        return embedding.tolist() if as_list else embedding

    @staticmethod
    def hash_text(text: str) -> bytes:
        """
        Generate SHA256 hash of input text.

        Args:
            text (str): The text to hash.

        Returns:
            bytes: SHA256 hash digest (32 bytes).
        """
        return sha256(text.encode("utf-8")).digest()
