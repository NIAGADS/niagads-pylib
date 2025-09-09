from enum import auto
from typing import List, Optional
from niagads.enums.core import CaseInsensitiveEnum
from transformers import pipeline


class SummarizationModel(CaseInsensitiveEnum):
    """
    Enum for selecting summarization models, case-insensitive.

    Members:
        PEGASUS_PUBMED: Biomedical summarization (google/pegasus-pubmed) - Specialized for biomedical literature, excels at condensing scientific abstracts and PubMed articles.
        BART_LARGE_CNN: General summarization (facebook/bart-large-cnn) - Versatile and robust, works well for a wide range of text but may lack biomedical nuance.
        LED_ARXIV: Long document summarization (allenai/led-base-16384-arxiv) - Designed for long scientific documents, can handle large biomedical reports or papers, but may be less domain-specific than PEGASUS.
    """

    PEGASUS_PUBMED = auto()
    BART_LARGE_CNN = auto()
    LED_ARXIV = auto()

    def __str__(self):
        if self == SummarizationModel.PEGASUS_PUBMED:
            return "google/pegasus-pubmed"
        elif self == SummarizationModel.BART_LARGE_CNN:
            return "facebook/bart-large-cnn"
        elif self == SummarizationModel.LED_ARXIV:
            return "allenai/led-base-16384-arxiv"
        else:
            raise ValueError(f"Unknown summarization model: {self}")


class TextSummarizer:
    """
    Summarizes context sentences for any set of keys (e.g., genes, topics) using an LLM summarization model.
    """

    def __init__(
        self,
        model: SummarizationModel = SummarizationModel.PEGASUS_PUBMED,
        max_length: int = 128,
        min_length: int = 32,
    ):
        self.__model = model or SummarizationModel.BART_LARGE_CNN
        self.__max_length = max_length
        self.__min_length = min_length
        self.__summarizer = pipeline("summarization", model=str(self.__model))

    def summarize(self, text_segments: List[str]) -> str:
        """
        Summarize the provided list of text segments using an LLM summarization model.
        Returns a summary string.
        Raises ValueError if text_segments is None or empty.
        """

        text = " ".join(text_segments)
        if len(text) > 2000:
            text = text[:2000]
        summary = self.__summarizer(
            text,
            max_length=self.__max_length,
            min_length=self.__min_length,
            do_sample=False,
        )[0]["summary_text"]
        return summary
