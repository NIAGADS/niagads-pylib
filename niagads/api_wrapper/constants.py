""" constants used by the API wrapper"""
from enum import auto
from strenum import StrEnum
from niagads.utils.enums import CustomStrEnum

PAGE_SIZES = [50, 100, 200, 300, 400, 500]
class RecordTypes(CustomStrEnum, StrEnum):
    """
    StrEnum - values can used as strings
    auto() sets enum value = ENUM
    """
    VARIANT = auto()
    GENE = auto()
    SPAN = auto()
    COLLECTION = auto()
    TRACK = auto()
    
    
class Databases(CustomStrEnum, StrEnum):
    GENOMICS = auto()
    FILER = auto()
    ADVP = auto()
    

class FileFormats(CustomStrEnum, StrEnum):
    TABLE = auto()
    JSON = auto()
    
    
class VariantConsequenceTypes(CustomStrEnum, StrEnum):
    MOST_SEVERE = 'most_severe_consequence'
    REGULATORY = 'regulatory_feature_consequences'
    ALL = 'ranked_consequences'
    TRANSCRIPT = 'transcript_consequences'
    MOTIF = 'motif_feature_consequences'
    