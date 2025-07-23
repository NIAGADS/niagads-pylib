from enum import auto
from niagads.api_common.parameters.enums import EnumParameter


class RankedConsequenceType(EnumParameter):
    """enum for type of ranked consequence"""

    MOTIF = auto()
    TRANSCRIPT = auto()
    REGULATORY = auto()
    INTERGENIC = auto()
    ALL = auto()

    def __str__(self):
        match self.name:
            case "MOTIF":
                return "Motif Regulatory Consequences"
            case "TRANSCRIPT":
                return "Transcript Consequences"
            case "REGULATORY":
                return "Regulatory Consequences"
            case "INTERGENIC":
                return "Intergenic Consequences"
            case _:
                return "All consequences"
