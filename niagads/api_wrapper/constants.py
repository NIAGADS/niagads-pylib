""" constants used by the API wrapper"""
from enum import auto
from strenum import StrEnum

PAGE_SIZES = [50, 100, 200, 300, 400, 500]
class RecordTypes(StrEnum):
    """
    StrEnum - values can used as strings
    auto() sets enum value = ENUM
    """
    VARIANT = auto()
    GENE = auto()
    SPAN = auto()
    COLLECTION = auto()
    TRACK = auto()
    
    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 
    
    @classmethod
    def list(self):
        return [e.value for e in self]
    
    
class Databases(StrEnum):
    GENOMICS = auto()
    FILER = auto()
    ADVP = auto()
    
    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 
    
    @classmethod
    def list(self):
        return [e.value for e in self]

class FileFormats(StrEnum):
    TABLE = auto()
    JSON = auto()
    
    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 
    
    @classmethod
    def list(self):
        return [e.value for e in self]
    
class VariantConsequenceTypes(StrEnum):
    MOST_SEVERE = 'most_severe_consequence'
    REGULATORY = 'regulatory_feature_consequences'
    ALL = 'ranked_consequences'
    TRANSCRIPT = 'transcript_consequences'
    MOTIF = 'motif_feature_consequences'
    
    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 
    
    @classmethod
    def list(self):
        return [e.value for e in self]
