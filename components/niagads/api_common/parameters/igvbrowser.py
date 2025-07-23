from enum import auto
from niagads.api_common.parameters.enums import EnumParameter


class ADSPRelease(EnumParameter):
    ADSP_17K = "17K"
    ADSP_R3 = "R3"
    ADSP_R4 = "R4"


class AnnotatedVariantTrack(EnumParameter):
    ADSP = auto()
    ADSP_SV = auto()
    DBSNP = auto()
    DBSNP_COMMON = auto()
