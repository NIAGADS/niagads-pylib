import difflib
from typing import List, Optional, Set

from niagads.common.core import ComponentBaseMixin

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None


class SynonymMatcher(ComponentBaseMixin):
    """
    WordNet-based synonym matcher for flexible string matching.

    About WordNet:
            WordNet is a large lexical database of English developed at
            Princeton University. Nouns, verbs, adjectives, and adverbs are grouped
            into sets of cognitive synonyms (synsets), each expressing a distinct
            concept. Synsets are interlinked by means of conceptual-semantic and
            lexical relations.

            This matcher uses the NLTK interface to WordNet to retrieve synonyms for
            words and short phrases.

            - WordNet official site:
                https://wordnet.princeton.edu/
            - NLTK WordNet documentation:
                https://www.nltk.org/howto/wordnet.html
            - NLTK project:
                https://www.nltk.org/

            For installation and usage instructions, see:
                    https://www.nltk.org/install.html
                    https://www.nltk.org/data.html
    """

    def __init__(
        self,
        words: List[str],
        threshold: float = 0.8,
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the SynonymMatcher.

        Args:
            reference_strings (List[str]): List of canonical reference strings to match against.
            threshold (float, optional): Fuzzy matching threshold (0-1, higher is stricter). Defaults to 0.8.
            debug (bool, optional): Enable debug logging. Defaults to False.
            verbose (bool, optional): Enable verbose logging. Defaults to False.
        """
        super().__init__(debug=debug, verbose=verbose)
        self._debug = debug
        self._verbose = verbose
        if self._debug:
            self.logger.setLevel = "DEBUG"
        self.__reference_words = words
        self.__threshold = self.set_threshold(threshold)
        self.__extended_words: Optional[Set[str]] = None

    @staticmethod
    def __validate_threshold(threshold):
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0 (inclusive).")

    def set_threshold(self, value: float):
        """
        Set the fuzzy matching threshold for string similarity.

        Args:
            value (float): The new threshold value.

        Raises:
            ValueError: If value is outside the allowable range.
        """
        self.__validate_threshold(value)
        self.__threshold = value

    def generate(self):
        """
        Generate synonyms for all reference strings using WordNet and build the match set.

        Raises:
            ImportError: If NLTK WordNet is not available.
        """
        if wn is None:
            raise ImportError(
                f"nltk.corpus.wordnet is not available. Please install nltk and "
                f"download wordnet data. See class docstring for more information."
            )
        self.__extended_words = set(s.lower() for s in self.__reference_words)
        for s in self.__reference_words:
            for syn in self._get_wordnet_synonyms(s):
                self.__extended_words.add(syn.lower().strip())

    def _get_wordnet_synonyms(self, text: str) -> Set[str]:
        """
        Get synonyms for a single word using WordNet.

        Args:
            text (str): The input word.

        Returns:
            Set[str]: A set of synonyms for the input word.
        """

        if "_" in text:
            self.logger.warning(
                f"Whitespace detected in text: {text}; synonym matching may not be accurate."
            )
        synonyms = set()
        for syn in wn.synsets(text):
            for lemma in syn.lemmas():
                synonym = lemma.name().replace("_", " ")
                if synonym.lower() != text.lower():
                    synonyms.add(synonym)
        return synonyms

    def match(self, query_string: str, allow_fuzzy: bool = True) -> bool:
        """
        Check if the query string matches any reference string or WordNet synonym.

        Args:
            query_string (str): The string to match against the reference set.
            allow_fuzzy (bool, optional): If True, allow fuzzy matching using difflib.
                If False, only exact matches are allowed. Defaults to True.

        Returns:
            bool: True if a match is found (case-insensitive, fuzzy or exact), otherwise False.
        """
        if not query_string or self.__extended_words is None:
            return False
        s = query_string.lower()
        if s in self.__extended_words:
            return True
        if allow_fuzzy:
            best = difflib.get_close_matches(
                s, self.__extended_words, n=1, cutoff=self.__threshold
            )
            return bool(best)
        return False

    def get_extended_synonyms(self) -> Optional[Set[str]]:
        """
        Return the set of all reference strings and their WordNet synonyms (lowercased).

        Returns:
            Optional[Set[str]]: The set of all matchable strings, or None if not generated.
        """
        if self.__extended_words is None:
            self.generate()
        return self.__extended_words
