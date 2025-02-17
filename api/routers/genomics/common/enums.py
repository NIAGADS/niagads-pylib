from enum import auto
from api.common.enums.base_enums import CaseInsensitiveEnum


class RecordType(CaseInsensitiveEnum):
    TRACK = auto()
    GENE = auto()
    VARIANT = auto()
    COLLECTION = auto()

class ConsequenceImpact(CaseInsensitiveEnum):
    HIGH = auto()
    MODERATE = auto()
    LOW = auto()
    MODIFIER = auto()