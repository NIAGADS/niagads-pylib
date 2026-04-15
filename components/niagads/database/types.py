from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class RAGDocType(CaseInsensitiveEnum):
    REFERENCE = auto()
    ONTOLOGY = auto()
    GENE = auto()
    VARIANT = auto()
    METADATA = auto()
    DOCUMENT = auto()


class RetrievalStatus(CaseInsensitiveEnum):
    PENDING = auto()
    IN_PROGRESS = auto()
    SUCCESS = auto()
    FAILED = auto()
