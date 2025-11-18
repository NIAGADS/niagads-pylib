"""
Asynchronous LLM-based paraphraser.
TODO: This is broken; and needs to be refactored as a paraphraser
TODO: handle one str, instead of a list
TODO: remove all references to synonyms
TODO: set prompt simply to `paraphrase`
"""

import asyncio
import difflib
from typing import List, Optional, Set

import torch
from niagads.common.core import ComponentBaseMixin
from niagads.nlp.core import NLPModel, NLPModelType, validate_llm_type
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class LLMParaphraser(ComponentBaseMixin):
    """
    sss   Asynchronous matcher that uses an LLM to generate synonyms for a list of reference strings.
       The matcher will match any string against the reference strings or their LLM-suggested synonyms.

       Usage:
           1. Instantiate with a list of reference strings and an NLPModel for paraphrasing (default: T5).
           2. Call `await generate()` to build the set of reference strings and their LLM-generated synonyms.
           3. Use `match(query_string)` to check if a string matches any reference or synonym (case-insensitive, with optional fuzzy matching).
           4. Use `get_extended_synonyms()` to retrieve the full set of matchable strings.

       This approach enables robust, context-aware string matching by leveraging LLM-based paraphrasing for dynamic synonym expansion.
    """

    def __init__(
        self,
        reference_strings: List[str],
        model: NLPModel = NLPModel.T5,
        threshold: float = 0.8,
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the LLMSynonymMatcher.

        Args:
            reference_strings (List[str]): List of canonical reference strings to match against.
            model (NLPModel, optional): The LLM model to use for synonym generation. Defaults to NLPModel.T5.
            threshold (float, optional): Fuzzy matching threshold (0-1, higher is stricter). Defaults to 0.8.
            debug (bool, optional): Enable debug logging. Defaults to False.
            verbose (bool, optional): Enable verbose logging. Defaults to False.
        """
        super().__init__(debug=debug, verbose=verbose)
        self._debug = debug
        self._verbose = verbose
        if self._debug:
            self.logger.setLevel = "DEBUG"

        self.__reference_strings = reference_strings
        self.__model_name = validate_llm_type(model, NLPModelType.PARAPHRASE)
        self.__threshold = self.set_threshold(threshold)
        self.__extended_strings: Optional[Set[str]] = None

        # Load model and tokenizer at initialization
        # some tokenizers use SentencePiece (e.g., T5) and do not have a fast tokenizer
        # leading to initialization errors, catch those and disable `use_fast`
        try:
            self.__tokenizer = AutoTokenizer.from_pretrained(
                self.__model_name, use_fast=True
            )
        except Exception:
            self.__tokenizer = AutoTokenizer.from_pretrained(
                self.__model_name, use_fast=False
            )

        self.__paraphraser = AutoModelForSeq2SeqLM.from_pretrained(self.__model_name)
        self.__device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Try to move model to GPU if available, but fall back to CPU if out of memory
        try:
            self.__paraphraser = self.__paraphraser.to(self.__device)
        except RuntimeError as e:
            if self.__device.type == "cuda" and "out of memory" in str(e).lower():
                self.logger.warning("CUDA out of memory. Falling back to CPU.")
                self.__device = torch.device("cpu")
                self.__paraphraser = self.__paraphraser.to(self.__device)
            else:
                raise

    @staticmethod
    def __validate_threshold(threshold):
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0 (inclusive).")

    def set_threshold(self, value: float):
        """
        Set the fuzzy matching threshold for string similarity.
        Value must be between 0.0 and 1.0 (inclusive).

        Recommended values:
            - 0.6–0.7: Broad, permissive matching (may include distant matches)
            - 0.8: Balanced (default)
            - 0.9–1.0: Strict, only very close or exact matches

        Adjust the threshold for your use case:
            - Lower for recall-oriented tasks (find more matches)
            - Higher for precision-oriented tasks (avoid false positives)

        Args:
            value (float): The new threshold value.

        Raises:
            ValueError: If value is outside the allowable range.
        """
        self.__validate_threshold(value)
        self.__threshold = value

    async def generate(self):
        """
        Asynchronously generate synonyms for all reference strings using the selected LLM and build the match set.
        Expands the set of matchable strings to include LLM-generated paraphrases for robust, context-aware matching.
        Call this before using `match()` or `get_extended_synonyms()`.
        """
        self.__extended_strings = set(s.lower() for s in self.__reference_strings)
        synonym_lists = await self._gather_synonyms()
        for syns in synonym_lists:
            self.__extended_strings.update(s.lower() for s in syns)

    async def _gather_synonyms(self) -> List[List[str]]:
        return await asyncio.gather(
            *(self._generate_synonyms(s) for s in self.__reference_strings)
        )

    def match(self, query_string: str) -> bool:
        """
        Check if the query string matches any reference string or LLM-generated synonym.

        Args:
            query_string (str): The string to match against the reference set.

        Returns:
            bool: True if a match is found (case-insensitive, fuzzy or exact), otherwise False.

        Note:
            Call `generate()` before using this method to ensure the synonym set is built.
        """
        if not query_string or self.__extended_strings is None:
            return False
        s = query_string.lower()
        # Direct match
        if s in self.__extended_strings:
            return True
        # Fuzzy match using difflib
        best = difflib.get_close_matches(
            s, self.__extended_strings, n=1, cutoff=self.__threshold
        )
        return bool(best)

    async def get_extended_synonyms(self, prompt: str) -> Optional[Set[str]]:
        """
        Return the set of all reference strings and their LLM-generated synonyms (lowercased).

        Returns:
            Optional[Set[str]]: The set of all matchable strings, or None if not generated.

        Note:
            If not yet generated, this will call `generate()` first.
        """
        if self.__extended_strings is None:
            await self.generate(prompt)
        return self.__extended_strings

    async def _generate_synonyms(self, text: str) -> List[str]:
        """
        Generate synonyms for the input text using the LLM specified by self.__model_name.
        Returns a list of unique paraphrases (excluding the original text).

        Args:
            text (str): The input text for which to generate synonyms.

        Returns:
            List[str]: A list of generated synonyms.
        """

        input_text = f"{self.__prompt.replace(':', '')} '{text}'."
        encoding = self.__tokenizer.encode_plus(
            input_text,
            padding="max_length",
            return_tensors="pt",
            max_length=64,
            truncation=True,
        )
        input_ids, attention_mask = (
            encoding["input_ids"].to(self.__device),
            encoding["attention_mask"].to(self.__device),
        )
        outputs = self.__paraphraser.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_length=64,
            num_beams=5,
            num_return_sequences=3,
            temperature=1.5,
            early_stopping=True,
        )
        paraphrases = set()
        for output in outputs:
            paraphrase = self.__tokenizer.decode(
                output, skip_special_tokens=True, clean_up_tokenization_spaces=True
            )
            if paraphrase.lower() != text.lower():
                paraphrases.add(paraphrase.strip())
        return list(paraphrases)
