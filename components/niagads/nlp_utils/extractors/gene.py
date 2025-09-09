from enum import auto
from typing import List

from niagads.enums.core import CaseInsensitiveEnum
from niagads.nlp_utils.core import segment_sentences
from niagads.nlp_utils.summarizer import TextSummarizer, SummarizationModel
from transformers import pipeline


class GeneNERModel(CaseInsensitiveEnum):
    """
    Enum for selecting gene/protein NER models, case-insensitive.

    Members:
        D4DATA: Biomedical NER (d4data/biomedical-ner-all) - General-purpose biomedical NER, robust for genes, proteins, diseases, and chemicals; good default for most biomedical text mining tasks.
        SAPBERT: Biomedical NER (cambridgeltl/SapBERT-from-PubMedBERT-fulltext-ner) - Based on PubMedBERT, may provide improved gene/protein recognition for biomedical literature, especially PubMed full text; can be more accurate for gene/protein-specific corpora.
    """

    D4DATA = auto()
    SAPBERT = auto()

    def __str__(self):
        if self == GeneNERModel.D4DATA:
            return "d4data/biomedical-ner-all"
        elif self == GeneNERModel.SAPBERT:
            return "cambridgeltl/SapBERT-from-PubMedBERT-fulltext-ner"
        else:
            raise ValueError(f"Unknown model: {self}")


class GeneReferenceExtractor:
    """
    Extracts references to gene symbols from a block of text using an LLM-based NER model.
    NER = Named Entity Recognition, a natural language processing (NLP) technique for identifying and classifying entities (such as genes, proteins, diseases, etc.) in text.
    """

    def __init__(self, model: GeneNERModel = GeneNERModel.D4DATA):
        self.__model = model
        # Initialize the Hugging Face NER pipeline for gene/protein extraction
        self.__ner_pipeline = pipeline(
            "ner", model=str(self.__model), aggregation_strategy="simple"
        )
        # Set of possible gene/protein entity labels (may vary by model)
        self.__gene_labels = {
            "GENE",
            "GENE_OR_GENE_PRODUCT",
            "GENE_OR_PROTEIN",
            "GENE_PROTEIN",
            "GENE_PRODUCT",
            "PROTEIN",
        }

    def extract(self, text: str) -> List[str]:
        """
        Extract references to gene symbols/entities from the input text.
        Returns a list of unique gene symbols/entities found in the text.
        """
        results = self.__ner_pipeline(text)
        genes = [
            entity["word"]
            for entity in results
            if entity.get("entity_group", entity.get("entity", "")).upper()
            in self.__gene_labels
        ]
        return list(sorted(set(genes)))

    def extract_gene_contexts(
        self,
        text: str,
        summarize: bool = False,
        summarizer_model: "SummarizationModel" = None,
    ) -> dict:
        """
        Extract gene mentions along with their surrounding context (sentence) from the input text.
        If summarize=True, returns a dict keyed on gene with a summary string per gene.
        Otherwise, returns a dict keyed on gene with a list of one or more sentences per gene.
        """
        sentences = segment_sentences(text)
        gene_contexts = {}
        for sentence in sentences:
            gene_mentions = set(self.extract(sentence))  # Unique genes per sentence
            for gene in gene_mentions:
                if gene not in gene_contexts:
                    gene_contexts[gene] = []
                gene_contexts[gene].append(sentence)
        if summarize:
            summarizer = TextSummarizer(model=summarizer_model)
            return summarizer.summarize(gene_contexts)
        return gene_contexts
