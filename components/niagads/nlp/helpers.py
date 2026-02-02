import re

import spacy
from niagads.nlp.constants import STOPWORDS
from niagads.nlp.llm_types import LLM, NLPModelType
from sentence_transformers import SentenceTransformer


def segment_sentences(text: str) -> list[str]:
    """
    Segment text into sentences using spaCy's sentencizer.

    Args:
        text (str): The input text to segment.

    Returns:
        List[str]: A list of sentence strings.
    """
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]


def chunk_text(text: str, max_chunk_size: int = 2000) -> list[str]:
    """
    Split text into chunks no longer than max_chunk_size, preserving sentence boundaries.

    Sentences are accumulated into each chunk using segment_sentences, so that
    no chunk exceeds max_chunk_size characters. This helps ensure that chunks
    are natural and readable for downstream processing.

    Args:
        text (str): The input text to split.
        max_chunk_size (int): Maximum number of characters per chunk.

    Returns:
        list[str]: List of text chunks, each no longer than max_chunk_size.
    """
    sentences = segment_sentences(text)
    chunks = []
    current_chunk = ""
    for sentence_fragment in sentences:
        # If adding this sentence would exceed the chunk size, start a new chunk
        if len(current_chunk) + len(sentence_fragment) + 1 > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence_fragment
        else:
            if current_chunk:
                current_chunk += " " + sentence_fragment
            else:
                current_chunk = sentence_fragment
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def tokenize(
    text: str | list[str], stopwords: set = STOPWORDS
) -> list[str] | list[list[str]]:
    """
    Tokenize input text(s) by lowercasing, removing stopwords, and filtering out short tokens.

    Args:
        text (str or list[str]): Input text or list of texts to tokenize.
        stopwords (set): Set of stopwords to remove from tokens.

    Returns:
        list[str] or list[list[str]]: List of tokens if input is a string, or list of token lists if input is a list of strings.

    Raises:
        ValueError: If input text is None or empty.
    """
    if not text:
        raise ValueError("Input text must not be None or empty.")

    is_single = isinstance(text, str)
    texts = [text] if is_single else text

    tokens_list = []
    for t in texts:
        tokens = re.findall(r"[a-z0-9\-]+", t.lower())
        tokens = [tok for tok in tokens if tok not in stopwords and len(tok) > 1]
        tokens_list.append(tokens)
    if is_single:
        return tokens_list[0]
    return tokens_list


def calculate_text_embedding(
    text: str,
    model_name: LLM = LLM.ALL_MINILM_L6_V2,
    normalize: bool = True,
    as_list: bool = True,
) -> list[float]:
    """
    Calculate a text embedding using SentenceTransformer.

    Args:
        text (str): The input text to embed.
        model_name (LLM): The embedding model to use. Defaults to ALL_MINILM_L6_V2.
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

    LLM.validate(model_name, NLPModelType.EMBEDDING)

    model = SentenceTransformer(model_name.value)
    embedding = model.encode(text, normalize_embeddings=normalize)
    return embedding.tolist() if as_list else embedding
