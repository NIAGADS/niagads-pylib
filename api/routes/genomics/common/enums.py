from enum import auto
from api.common.enums.base_enums import CaseInsensitiveEnum

class ConsequenceImpact(CaseInsensitiveEnum):
    HIGH = auto()
    MODERATE = auto()
    LOW = auto()
    MODIFIER = auto()