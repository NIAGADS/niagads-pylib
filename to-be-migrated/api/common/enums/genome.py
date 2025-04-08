from enum import StrEnum, auto
from api.common.enums.base_enums import EnumParameter

class Strand(StrEnum):
    SENSE = '+'
    ANTISENSE = '-'
    
    def __str__(self):
        return self.value


class Assembly(EnumParameter):
    """enum for genome builds"""
    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"
        
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        if value.lower() == 'hg19': return cls.GRCh37
        if value.lower() == 'hg38': return cls.GRCh38
        return super(Assembly, cls)._missing_(value)
    
    
class FeatureType(StrEnum): # needs CustomStrEnum.list
    GENE = auto()
    VARIANT = auto()
    STRUCTURAL_VARIANT = auto()
    SPAN = auto()
    
    @classmethod
    def list(self):
        """ return a list of all values in the StrEnum """
        return [e.value for e in self]
