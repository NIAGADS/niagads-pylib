import re

import spacy
from niagads.nlp.constants import STOPWORDS


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
