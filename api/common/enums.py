from enum import Enum
from itertools import chain

class CaseInsensitiveEnum(str, Enum):
    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        for member in cls:
            if member.value.lower() == value.lower(): 
                return member
    
        raise KeyError(value)
    
class ResponseContent(CaseInsensitiveEnum):
    """ enum for allowable response types """
    FULL = "full"
    COUNTS = "counts"
    IDS = "ids"
    SUMMARY = "summary"

class ResponseFormat(CaseInsensitiveEnum):
    """ enum for allowable response / output formats"""
    JSON = "json"
    TABLE = "table"
    

class Assembly(str, Enum):
    """enum for genome builds"""
    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"
    hg19 = "hg19"
    hg38 = "hg38"
        
    def validate(self):
        return "GRCh37" if self.value.lower() == 'hg19' \
            else "GRCh38" if self.value.lower() == 'hg38' else self.value
