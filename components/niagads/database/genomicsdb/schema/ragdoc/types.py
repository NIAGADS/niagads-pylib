from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class RAGDocTypes(CaseInsensitiveEnum):
    REFERENCE = auto()
    ONTOLOGY = auto()
    GENE = auto()
    VARIANT = auto()
    METADATA = auto()
    DOCUMENT = auto()
