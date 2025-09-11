import re
import warnings
from enum import auto
from typing import List

import spacy
from niagads.enums.core import CaseInsensitiveEnum
from transformers import AutoConfig


class NLPModelType(CaseInsensitiveEnum):
    """
    Enum for specifying model type categories.

    Members:
        SUMMARIZATION: Models used for summarization tasks.
        EMBEDDING: Models used for generating embeddings.
        NER: Models used for Named Entity Recognition.
        SYNONYM: Models used for synonym generation or paraphrasing.
    """

    SUMMARIZATION = auto()
    EMBEDDING = auto()
    NER = auto()
    SYNONYM = auto()


class NLPModel(CaseInsensitiveEnum):
    """
    Enum for selecting NLP models (summarization, embedding, NER, synonym generation), case-insensitive.

    Members:
        PEGASUS_PUBMED: Biomedical summarization (google/pegasus-pubmed)
        BART_LARGE_CNN: General summarization (facebook/bart-large-cnn)
        LED_ARXIV: Long document summarization (allenai/led-base-16384-arxiv)
        ALL_MINILM_L6_V2: General-purpose sentence embedding (sentence-transformers/all-MiniLM-L6-v2)
        BIOBERT_MNLI_SNLI: Biomedical/scientific sentence embedding (pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb)
        SPECTER: Scientific/biomedical paper embedding (sentence-transformers/allenai-specter)
        D4DATA: Biomedical NER (d4data/biomedical-ner-all)
        SAPBERT: Biomedical NER (cambridgeltl/SapBERT-from-PubMedBERT-fulltext-ner)
        BENT_PUBMEDBERT_VARIANT: Biomedical NER (pruas/BENT-PubMedBERT-NER-Variant)
        T5: T5 paraphrase model (Vamsi/T5_Paraphrase_Paws)
        BART_PARAPHRASE: BART paraphrase model (eugenesiow/bart-paraphrase)
    """

    PEGASUS_PUBMED = auto()
    BART_LARGE_CNN = auto()
    LED_ARXIV = auto()
    ALL_MINILM_L6_V2 = auto()
    BIOBERT_MNLI_SNLI = auto()
    SPECTER = auto()
    D4DATA = auto()
    SAPBERT = auto()
    BENT_PUBMEDBERT_VARIANT = auto()
    T5 = auto()
    BART_PARAPHRASE = auto()

    _MODEL_TYPE_MAP = {
        PEGASUS_PUBMED: NLPModelType.SUMMARIZATION,
        BART_LARGE_CNN: NLPModelType.SUMMARIZATION,
        LED_ARXIV: NLPModelType.SUMMARIZATION,
        ALL_MINILM_L6_V2: NLPModelType.EMBEDDING,
        BIOBERT_MNLI_SNLI: NLPModelType.EMBEDDING,
        SPECTER: NLPModelType.EMBEDDING,
        D4DATA: NLPModelType.NER,
        SAPBERT: NLPModelType.NER,
        BENT_PUBMEDBERT_VARIANT: NLPModelType.NER,
        T5: NLPModelType.SYNONYM,
        BART_PARAPHRASE: NLPModelType.SYNONYM,
    }

    def __str__(self):
        if self == NLPModel.PEGASUS_PUBMED:
            return "google/pegasus-pubmed"
        elif self == NLPModel.BART_LARGE_CNN:
            return "facebook/bart-large-cnn"
        elif self == NLPModel.LED_ARXIV:
            return "allenai/led-base-16384-arxiv"
        elif self == NLPModel.ALL_MINILM_L6_V2:
            return "sentence-transformers/all-MiniLM-L6-v2"
        elif self == NLPModel.BIOBERT_MNLI_SNLI:
            return "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb"
        elif self == NLPModel.SPECTER:
            return "sentence-transformers/allenai-specter"
        elif self == NLPModel.D4DATA:
            return "d4data/biomedical-ner-all"
        elif self == NLPModel.SAPBERT:
            return "cambridgeltl/SapBERT-from-PubMedBERT-fulltext-ner"
        elif self == NLPModel.BENT_PUBMEDBERT_VARIANT:
            return "pruas/BENT-PubMedBERT-NER-Variant"
        elif self == NLPModel.T5:
            return "Vamsi/T5_Paraphrase_Paws"
        elif self == NLPModel.BART_PARAPHRASE:
            return "eugenesiow/bart-paraphrase"
        else:
            return self._missing_()

    @property
    def model_type(self) -> NLPModelType:
        """
        Return the NLPModelType for this model.
        """
        return self._MODEL_TYPE_MAP[self]

    @classmethod
    def validate(cls, model, model_type: NLPModelType):
        model_enum = cls(model)
        if model_enum.model_type != model_type:
            raise ValueError(f"{model} is not a valid {model_type.name.lower()} model.")
        return model

    @classmethod
    def _missing_(cls, value=None):
        """
        Handle missing enum values for NLPModel.
        If the value is a valid Hugging Face model name, return it with a warning.
        If not, raise a ValueError.
        """
        try:
            AutoConfig.from_pretrained(value)
        except Exception:
            raise ValueError(
                f"Model '{value}' is not registered in this library and could not be found on Hugging Face. Please check the model name."
            )

        warnings.warn(
            f"Model '{value}' is not registered in this library, but is a valid Hugging Face model. Please ensure it is suitable for your intended use."
        )
        return value


def validate_llm_type(model: NLPModel, model_type: NLPModelType) -> str:
    """
    Validate that the given model is of the specified model_type.

    Args:
        model (NLPModel or str): The model to validate. Can be an NLPModel enum or a string representing the model.
        model_type (NLPModelType): The required type of the model (e.g., SUMMARIZATION, EMBEDDING).

    Returns:
        str: The Hugging Face model name if validation passes.

    Raises:
        ValueError: If the model is not of the specified model_type.
    """
    return str(NLPModel.validate(model, model_type))


STOPWORDS = {
    "the",
    "and",
    "of",
    "in",
    "on",
    "for",
    "with",
    "a",
    "an",
    "to",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "study",
    "studies",
    "patients",
    "subjects",
    "using",
}


def segment_sentences(text: str) -> List[str]:
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
