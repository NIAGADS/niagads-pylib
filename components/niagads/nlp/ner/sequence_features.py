import re

from niagads.nlp.core import (
    NLPModel,
    NLPModelType,
    segment_sentences,
    validate_llm_type,
)
from niagads.nlp.ner.core import EntityNER
from niagads.utils.regular_expressions import RegularExpressions
from transformers import pipeline


class GeneNER(EntityNER):
    """
    Identifies gene/protein references and their contexts in text using an LLM-based NER model.
    """

    LABELS = {
        "GENE",
        "GENE_OR_GENE_PRODUCT",
        "GENE_OR_PROTEIN",
        "GENE_PROTEIN",
        "GENE_PRODUCT",
        "PROTEIN",
    }

    def __init__(
        self,
        model: NLPModel = NLPModel.D4DATA,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(model=model, debug=debug, verbose=verbose)


# XXX: no good NER model currently exists for variants and certainly not SV
# research gap worth exploring

# TODO: chunking for association extraction


class VariantNER(EntityNER):
    """
    Identifies variant references and their contexts in text using an LLM-based NER model.
    """

    LABELS = {
        "VARIANT",
        "GENOMIC_VARIANT",
        "MUTATION",
        "SNP",
        "SNV",
        "INDEL",
        "INS",
        "DEL",
        "DUP",
        "CNV",
        "SV",
        "INSERTION",
        "DELETION",
        "DUPLICATION",
        "TRANSLOCATION",
        "INVERSION",
        "COPY_NUMBER_VARIATION",
    }

    def __init__(
        self,
        model: NLPModel = NLPModel.BENT_PUBMEDBERT_VARIANT,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(model=model, debug=debug, verbose=verbose)

    # TODO: broaden the context and capture the disease-risk association
    def associations(
        self,
        text: str,
        use_llm: bool = True,
        llm_model: NLPModel = NLPModel.BIOGPT_LARGE,
    ) -> dict:
        """
        Hybrid approach: For each variant mention in the text, extract p-value/statistical references associated with it.
        If use_ner is True, use NER-based context extraction; if False, use LLM prompt-based association.

        Use the NER approach for fast, structured extraction when the text is well-formed and entity boundaries are clear.
        Use the prompt-based LLM approach for more complex, ambiguous, or context-dependent associations where
        deeper reasoning or flexible language understanding is required.

        Args:
            text (str): Input text to analyze for variant-pvalue associations.
            use_ner (bool): If True, use NER-based method. If False, use LLM prompt-based method.
            llm_model (NLPModel): Model to use for prompt-based analysis (default: BIOMED_GPT4 or similar biomedical LLM).

        Returns:
            dict: Mapping from variant mention (str) to list of p-value/statistical reference strings associated with it.
        """
        if use_llm:
            return self._associations_llm(text, llm_model)
        else:
            return self._associations_ner(text)

    def _associations_ner(self, text: str) -> dict:
        """
        NER-based: For each variant mention in the text, extract p-value/statistical references that are contextually linked to it.
        Uses parent class methods for reference and context extraction.
        """
        pval_pattern = re.compile(RegularExpressions.PVALUE_STATEMENT, re.IGNORECASE)
        variant_to_pvals = {}

        # Use parent method to get all variant references and their contexts (sentences)
        variant_contexts = self.contexts(text)  # returns List[Tuple[str, str]]
        for variant, context in variant_contexts:
            pvals = [m.strip() for m in pval_pattern.findall(context)]
            if pvals:
                if variant not in variant_to_pvals:
                    variant_to_pvals[variant] = []
                variant_to_pvals[variant].extend(pvals)

        # Remove duplicates and sort
        for variant in variant_to_pvals:
            variant_to_pvals[variant] = list(sorted(set(variant_to_pvals[variant])))
        return variant_to_pvals

    def _associations_llm(self, text: str, llm_model: NLPModel) -> dict:
        """
        LLM prompt-based: For each variant mention, use an LLM to extract the associated p-value/statistical reference from the text.
        """
        llm_pipe = pipeline(
            "text-generation", model=validate_llm_type(llm_model, NLPModelType.LLM)
        )
        variants = self.references(text)
        mapping = {}
        for variant in variants:
            prompt = (
                f"In the following text, what is the p-value or statistical reference associated with the variant '{variant}'? "
                f"Text: {text}"
            )
            response = llm_pipe(prompt, max_length=100)[0]["generated_text"]
            mapping[variant] = response.strip()
        return mapping
