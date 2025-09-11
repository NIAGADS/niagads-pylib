from niagads.common.core import ComponentBaseMixin
from niagads.nlp.core import (
    NLPModel,
    NLPModelType,
    chunk_text as _chunk_text,
    validate_llm_type,
)
from transformers import pipeline


class LLMSummarizer(ComponentBaseMixin):
    """
    Summarizes context sentences using an LLM summarization model.
    """

    def __init__(
        self,
        model: NLPModel = NLPModel.PEGASUS_PUBMED,
        max_length: int = 128,
        min_length: int = 32,
        debug: bool = False,
        verbose: bool = False,
        max_chunk_size: int = 2000,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__model: str = validate_llm_type(model, NLPModelType.SUMMARIZATION)
        self.__max_length: int = max_length
        self.__min_length: int = min_length
        self.__summarizer: any = pipeline("summarization", model=self.__model)
        self.__max_chunk_size: int = max_chunk_size
        if self._verbose:
            self.logger.info(
                f"LLMSummarizer initialized with model={self.__model}, max_length={self.__max_length}, min_length={self.__min_length}, debug={self._debug}, verbose={self._verbose}, chunking={self.__chunking}, max_chunk_size={self.__max_chunk_size}"
            )

    def chunk_text(self, text: str) -> list[str]:
        # Simple chunking by character count; can be improved to split on sentence boundaries
        if self._debug:
            self.logger.debug(
                f"Chunking text of length {len(text)} with max_chunk_size={self.__max_chunk_size}"
            )
        return _chunk_text(text, self.__max_chunk_size)

    def summarize(self, text_segments: list[str], truncate: bool = False) -> str:
        """
        Summarize the provided list of text segments using an LLM summarization model.

        If the combined input text exceeds the maximum chunk size and truncate is False,
        the text will be split into chunks, each chunk summarized individually, and the
        chunk summaries will be summarized again for a final result. If truncate is True,
        only the first max_chunk_size characters are used.

        Args:
            text_segments (list[str]): List of text segments to summarize.
            truncate (bool): If True, truncate input to max_chunk_size. If False, chunk and summarize.

        Returns:
            str: The generated summary string.

        Raises:
            ValueError: If text_segments is None or empty.
        """
        if not text_segments:
            if self._debug:
                self.logger.warning("text_segments is None or empty.")
            raise ValueError("text_segments must not be None or empty.")

        if self._debug:
            self.logger.debug(f"summarize called with {len(text_segments)} segments.")

        text = " ".join(text_segments)

        if not truncate and len(text) > self.__max_chunk_size:
            return self._summarize_chunked(text)
        else:
            return self._summarize_single(text, truncate=truncate)

    def _summarize_chunked(self, text: str) -> str:
        """
        Summarize text by splitting into chunks and summarizing each chunk, then summarizing the summaries.
        """
        if self._debug:
            self.logger.debug(
                f"Input text length {len(text)} exceeds {self.__max_chunk_size}, chunking enabled."
            )

        chunks = self.chunk_text(text)
        summaries = []

        for idx, chunk in enumerate(chunks):
            if self._debug:
                self.logger.debug(
                    f"Summarizing chunk {idx+1}/{len(chunks)} (length {len(chunk)})"
                )
            summary = self._summarize_single(chunk)
            summaries.append(summary)
            if self._debug:
                self.logger.debug(
                    f"Chunk {idx+1} summary generated (length {len(summary)})."
                )
            if self._verbose:
                self.logger.info(f"Chunk {idx+1} summary: {summary}")

        # Optionally, summarize the summaries for a final result
        if len(summaries) > 1:
            if self._debug:
                self.logger.debug("Summarizing combined chunk summaries.")
            return self._summarize_single(" ".join(summaries))
        return summaries[0]

    def _summarize_single(self, text: str, truncate: bool = False) -> str:
        """
        Summarize a single text segment, truncating if necessary.
        """
        # Truncate if needed
        if len(text) > self.__max_chunk_size:
            if self._debug:
                self.logger.debug(
                    f"Input text length {len(text)} exceeds {self.__max_chunk_size}, truncating."
                )
            text = text[: self.__max_chunk_size]

        try:
            summary = self.__summarizer(
                text,
                max_length=self.__max_length,
                min_length=self.__min_length,
                do_sample=False,
            )[0]["summary_text"]

            if self._debug:
                self.logger.debug(f"Summary generated (length {len(summary)}).")
            if self._verbose:
                self.logger.info(f"Summary: {summary}")
            return summary
        except Exception as e:
            self.logger.error(f"Exception during summarization: {e}")
            raise
