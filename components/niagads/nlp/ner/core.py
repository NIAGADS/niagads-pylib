from typing import List

from niagads.common.core import ComponentBaseMixin
from niagads.nlp.analyzers.summarizer import LLMSummarizer
from niagads.nlp.core import (
    NLPModel,
    NLPModelType,
    segment_sentences,
    validate_llm_type,
)
from transformers import pipeline

# TODO: chunking?


class EntityNER(ComponentBaseMixin):
    """
    Base class for extracting entity references and their contexts from text using an LLM-based NER model.
    NER = Named Entity Recognition, a natural language processing (NLP) technique for identifying and classifying entities (such as genes, proteins, diseases, etc.) in text.

    Subclasses must define LABELS and docstrings.
    """

    LABELS: set = set()

    def __init__(
        self,
        model: NLPModel,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__model = validate_llm_type(model, NLPModelType.NER)
        self.__ner_pipeline = pipeline(
            "ner", model=self.__model, aggregation_strategy="simple"
        )

    def references(self, text: str) -> List[str]:
        """
        Extract and return unique entity references found in the input text using the NER pipeline.

        Args:
            text (str): Input text to analyze for entity mentions.

        Returns:
            List[str]: Sorted list of unique entity symbols/entities found in the text.
        """
        results = self.__ner_pipeline(text)
        entities = [
            entity["word"]
            for entity in results
            if entity.get("entity_group", entity.get("entity", "")).upper()
            in self.LABELS
        ]
        return list(sorted(set(entities)))

    def contexts(
        self,
        text: str,
        summarize: bool = False,
        summarizer_model: NLPModel = NLPModel.PEGASUS_PUBMED,
    ) -> dict:
        """
        Return a mapping of each entity reference to its sentence-level context(s) in the input text.

        Args:
            text (str): Input text to analyze for entity mentions and their contexts.
            summarize (bool): If True, summarize the context for each entity using a summarization model. Default is False.
            summarizer_model (NLPModel): Model to use for summarization if summarize=True. Default is NLPModel.PEGASUS_PUBMED ('google/pegasus-pubmed').

        Returns:
            dict: If summarize is False, returns a dict mapping each entity to a list of sentences mentioning it.
                  If summarize is True, returns a dict mapping each entity to a summary string.
        """
        sentences = segment_sentences(text)
        entity_contexts = {}
        for sentence in sentences:
            entity_mentions = set(self.references(sentence))
            for entity in entity_mentions:
                if entity not in entity_contexts:
                    entity_contexts[entity] = []
                entity_contexts[entity].append(sentence)
        if summarize:
            summarizer = LLMSummarizer(
                model=summarizer_model, debug=self._debug, verbose=self._verbose
            )
            return summarizer.summarize(entity_contexts)
        return entity_contexts
