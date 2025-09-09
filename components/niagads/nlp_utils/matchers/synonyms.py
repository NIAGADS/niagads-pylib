"""
Asynchronous LLM-based synonym matcher for flexible string matching.

This class enables robust string matching by using an LLM to generate synonyms for a list of reference strings.
- On initialization, you provide reference strings and a model name ('bart' or 't5').
- Call `await prepare()` to fetch synonyms for each reference string using the LLM and build the match set.
- Use `match(query_string)` to check if a string matches any reference or synonym (case-insensitive, with optional fuzzy matching).
- This approach allows dynamic, domain-adaptive synonym expansion for context-aware matching.
"""

from enum import auto
from typing import List, Optional
import difflib
from niagads.enums.core import CaseInsensitiveEnum
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import asyncio
import logging


class SynonymModel(CaseInsensitiveEnum):
    """
    Enum for selecting synonym generation models, case-insensitive.

    Members:
        T5: T5 paraphrase model (Vamsi/T5_Paraphrase_Paws) - Fast, general-purpose, and often robust for biomedical text, but may produce simpler paraphrases.
        BART: BART paraphrase model (eugenesiow/bart-paraphrase) - Can generate more diverse and fluent paraphrases, sometimes better for nuanced biomedical language, but may be slower and more resource-intensive.
    """

    T5 = auto()
    BART = auto()

    def __str__(self):
        if self == SynonymModel.T5:
            return "Vamsi/T5_Paraphrase_Paws"
        elif self == SynonymModel.BART:
            return "eugenesiow/bart-paraphrase"
        else:
            raise ValueError(f"Unknown synonym model: {self}")


class LLMSynonymMatcher:
    """
    Asynchronous matcher that uses an LLM to generate synonyms for a list of reference strings.
    The matcher will match any string against the reference strings or their LLM-suggested synonyms.

    How it works:
    1. You provide a list of reference strings and a model name ('bart' or 't5').
    2. Call `await prepare()` to fetch synonyms for each reference string using the LLM.
    3. The matcher builds a set of all reference strings and their synonyms (lowercased).
    4. Use `match(query_string)` to check if a string matches any reference or synonym (case-insensitive, with optional fuzzy matching).
    5. Fuzzy matching uses difflib with a configurable threshold.
    """

    def __init__(
        self,
        reference_strings: List[str],
        model: SynonymModel = SynonymModel.T5,
        threshold: float = 0.8,
        debug: bool = False,
        verbose: bool = False,
    ):
        self._debug = debug
        self._verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__reference_strings = reference_strings
        self.__model = str(model)
        self.__threshold = threshold
        self.__extended_strings: Optional[set] = None

    async def prepare(self):
        """
        Asynchronously fetch synonyms for all reference strings using the selected LLM and build the match set.
        This enables robust, context-aware matching by expanding the set of matchable strings.
        """
        self.__extended_strings = set(s.lower() for s in self.__reference_strings)
        # Gather all synonyms asynchronously using the selected model
        synonym_lists = await self.__gather_synonyms()
        # Add all lowercased synonyms to the match set
        for syns in synonym_lists:
            self.__extended_strings.update(s.lower() for s in syns)

    async def __gather_synonyms(self) -> List[List[str]]:
        # Use the unified synonym generator with the selected model
        return await asyncio.gather(
            *(
                self.__generate_synonyms(s, self.__model)
                for s in self.__reference_strings
            )
        )

    def match(self, query_string: str) -> bool:
        """
        Match a string against the reference strings and their LLM-suggested synonyms.
        Returns True if the query matches any reference or synonym (case-insensitive, with optional fuzzy matching).
        Call prepare() before using this method.
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

    async def get_extended_synonyms(self) -> Optional[set]:
        """
        Return the set of all reference strings and their LLM-generated synonyms (lowercased).
        If not yet prepared, this will call prepare() first.
        """
        if self.__extended_strings is None:
            await self.prepare()
        return self.__extended_strings

    @staticmethod
    async def __generate_synonyms(text: str, model: SynonymModel) -> List[str]:
        """
        Generate synonyms using a Seq2Seq model (T5 or BART) fine-tuned for paraphrasing.
        Model is selected via SynonymModel enum.
        """
        model_name = str(model)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model_obj = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_obj = model_obj.to(device)
        input_text = f"paraphrase: {text}"
        encoding = tokenizer.encode_plus(
            input_text,
            padding="max_length",
            return_tensors="pt",
            max_length=64,
            truncation=True,
        )
        input_ids, attention_mask = (
            encoding["input_ids"].to(device),
            encoding["attention_mask"].to(device),
        )
        outputs = model_obj.generate(
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
            paraphrase = tokenizer.decode(
                output, skip_special_tokens=True, clean_up_tokenization_spaces=True
            )
            if paraphrase.lower() != text.lower():
                paraphrases.add(paraphrase.strip())
        return list(paraphrases)


# Usage:
# matcher = LLMSynonymMatcher(["Conclusion", "Results", "Discussion"], SynonymModel.T5)
# await matcher.prepare()
# result = matcher.match("Summary")
#
# matcher_bart = LLMSynonymMatcher(["Conclusion", "Results", "Discussion"], SynonymModel.BART)
# await matcher_bart.prepare()
# result_bart = matcher_bart.match("Summary")
