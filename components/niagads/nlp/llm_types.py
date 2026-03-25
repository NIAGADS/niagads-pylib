import warnings
from enum import auto
from typing import List, Tuple

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
        LLM: Models used for general or prompt-based large language model tasks (biomedical chat, reasoning, etc.)
    """

    SUMMARIZATION = auto()
    EMBEDDING = auto()
    NER = auto()
    PARAPHRASE = auto()
    LLM = auto()


class LLM(CaseInsensitiveEnum):
    """
    Enum for selecting NLP models (summarization, embedding, NER, synonym generation, LLM), case-insensitive.

    Members:
        PEGASUS_PUBMED: Biomedical summarization (google/pegasus-pubmed). Excellent for summarizing PubMed abstracts and biomedical literature.
        BART_LARGE_CNN: General summarization (facebook/bart-large-cnn). Strong for news and general domain summarization.
        LED_ARXIV: Long document summarization (allenai/led-base-16384-arxiv). Designed for summarizing long scientific documents, especially arXiv papers.
        ALL_MINILM_L6_V2: General-purpose sentence embedding (sentence-transformers/all-MiniLM-L6-v2). Fast, lightweight, and effective for semantic similarity and clustering.
        BIOBERT_MNLI_SNLI: Biomedical/scientific sentence embedding (pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb). Specialized for biomedical and scientific text embeddings.
        SPECTER: Scientific/biomedical paper embedding (sentence-transformers/allenai-specter). State-of-the-art for scientific document similarity and citation prediction.
        D4DATA: Biomedical NER (d4data/biomedical-ner-all). Robust for extracting biomedical entities (genes, diseases, chemicals, etc.) from text.
        SAPBERT: Biomedical NER (cambridgeltl/SapBERT-from-PubMedBERT-fulltext-ner). Strong for biomedical entity normalization and NER.
        BENT_PUBMEDBERT_VARIANT: Biomedical NER (pruas/BENT-PubMedBERT-NER-Variant). Focused on variant and mutation extraction in biomedical literature.
        T5: T5 paraphrase model (Vamsi/T5_Paraphrase_Paws). General-purpose paraphrasing, good for data augmentation.
        BART_PARAPHRASE: BART paraphrase model (eugenesiow/bart-paraphrase). General-purpose paraphrasing, strong for diverse rewording.
        BIOGPT_LARGE: Biomedical LLM (microsoft/BioGPT-Large). Prompt-based biomedical reasoning, generation, and Q&A; excels at biomedical knowledge tasks.
        BIOMEDLM: Biomedical LLM (stanford-crfm/BioMedLM). GPT-3 style, strong for biomedical text generation, reasoning, and Q&A.
        PUBMEDGPT: Biomedical LLM (stanford-crfm/pubmedgpt). GPT-2 style, trained on PubMed abstracts; good for biomedical text generation and completion.
        MEDALPACA: Biomedical LLM (medalpaca/medalpaca-7b). Instruction-tuned for medical Q&A and reasoning, excels at following prompts in clinical/biomedical contexts.
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
    BIOGPT_LARGE = auto()
    BIOMEDLM = auto()
    PUBMEDGPT = auto()
    MEDALPACA = auto()

    def __str__(self):
        if self == LLM.PEGASUS_PUBMED:
            return "google/pegasus-pubmed"
        elif self == LLM.BART_LARGE_CNN:
            return "facebook/bart-large-cnn"
        elif self == LLM.LED_ARXIV:
            return "allenai/led-base-16384-arxiv"
        elif self == LLM.ALL_MINILM_L6_V2:
            return "sentence-transformers/all-MiniLM-L6-v2"
        elif self == LLM.BIOBERT_MNLI_SNLI:
            return "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb"
        elif self == LLM.SPECTER:
            return "sentence-transformers/allenai-specter"
        elif self == LLM.D4DATA:
            return "d4data/biomedical-ner-all"
        elif self == LLM.SAPBERT:
            return "cambridgeltl/SapBERT-from-PubMedBERT-fulltext-ner"
        elif self == LLM.BENT_PUBMEDBERT_VARIANT:
            return "pruas/BENT-PubMedBERT-NER-Variant"
        elif self == LLM.T5:
            return "Vamsi/T5_Paraphrase_Paws"
        elif self == LLM.BART_PARAPHRASE:
            return "eugenesiow/bart-paraphrase"
        elif self == LLM.BIOGPT_LARGE:
            return "microsoft/BioGPT-Large"
        elif self == LLM.BIOMEDLM:
            return "stanford-crfm/BioMedLM"
        elif self == LLM.PUBMEDGPT:
            return "stanford-crfm/pubmedgpt"
        elif self == LLM.MEDALPACA:
            return "medalpaca/medalpaca-7b"
        else:
            return self._missing_()

    @property
    def model_type(self) -> NLPModelType:
        """
        Return the NLPModelType for this model.
        """
        if self == LLM.PEGASUS_PUBMED:
            return NLPModelType.SUMMARIZATION
        elif self == LLM.BART_LARGE_CNN:
            return NLPModelType.SUMMARIZATION
        elif self == LLM.LED_ARXIV:
            return NLPModelType.SUMMARIZATION
        elif self == LLM.ALL_MINILM_L6_V2:
            return NLPModelType.EMBEDDING
        elif self == LLM.BIOBERT_MNLI_SNLI:
            return NLPModelType.EMBEDDING
        elif self == LLM.SPECTER:
            return NLPModelType.EMBEDDING
        elif self == LLM.D4DATA:
            return NLPModelType.NER
        elif self == LLM.SAPBERT:
            return NLPModelType.NER
        elif self == LLM.BENT_PUBMEDBERT_VARIANT:
            return NLPModelType.NER
        elif self == LLM.T5:
            return NLPModelType.PARAPHRASE
        elif self == LLM.BART_PARAPHRASE:
            return NLPModelType.PARAPHRASE
        elif self == LLM.BIOGPT_LARGE:
            return NLPModelType.LLM
        elif self == LLM.BIOMEDLM:
            return NLPModelType.LLM
        elif self == LLM.PUBMEDGPT:
            return NLPModelType.LLM
        elif self == LLM.MEDALPACA:
            return NLPModelType.LLM
        else:
            # return NLPModelType.LLM
            raise ValueError(
                f"Cannot validate NLP model type for unknown NLPModel: {self}"
            )

    @classmethod
    def validate(cls, model, model_type: NLPModelType):
        model_enum = cls(model)
        if model_enum.model_type != model_type:
            raise ValueError(
                f"`{model}` is not a valid `{model_type.name}` model. "
                f"Please select from the following {LLM.list(model_type)} "
                f"or update the list of valid `{model_type.name}` models "
                f"in the component `niagads.nlp.types.LLM`."
            )
        return model_enum

    def is_valid(self, model_type: NLPModelType):
        return self.validate(self, model_type)

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

    @classmethod
    def list(cls, model_type: NLPModelType = None) -> List[Tuple[str, str, str]]:
        """
        List all NLPModel members, or only those matching the specified NLPModelType.

        Args:
            model_type (NLPModelType, optional): If provided, only models of this type are listed.

        Returns:
            List[Tuple[str, str, str]]: List of (member name, Hugging Face model string, documentation string)
        """
        results = []
        member: LLM
        for member in cls:
            if model_type is None or member.model_type == model_type:
                doc = cls.__doc__ or ""
                doc_lines = [
                    l.strip()
                    for l in doc.splitlines()
                    if l.strip().startswith(f"{member.name}:")
                ]
                doc_str = doc_lines[0] if doc_lines else ""
                results.append((member.name, str(member), doc_str))
        return results
