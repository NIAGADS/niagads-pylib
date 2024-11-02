from enum import auto, Enum
from strenum import StrEnum
from aiocache.serializers import StringSerializer, JsonSerializer, PickleSerializer

class CaseInsensitiveEnum(StrEnum):
    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        for member in cls:
            if member.value.lower() == value.lower(): 
                return member
    
        raise KeyError(value)
    
class ResponseContent(CaseInsensitiveEnum):
    """ enum for allowable response types """
    FULL = auto()
    COUNTS = auto()
    IDS = auto()
    SUMMARY = auto()

class ResponseFormat(CaseInsensitiveEnum):
    """ enum for allowable response / output formats"""
    JSON = auto()
    TABLE = auto()
    DATA_BROWSER = auto()
    

class Assembly(str, Enum):
    """enum for genome builds"""
    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"
    hg19 = "hg19"
    hg38 = "hg38"
        
    def validate(self):
        return "GRCh37" if self.value.lower() == 'hg19' \
            else "GRCh38" if self.value.lower() == 'hg38' else self.value

class OnRowSelect(CaseInsensitiveEnum):
    """ enum for allowable NIAGADS-viz-js/Table onRowSelect actions """
    ACCESS_ROW_DATA = auto()
    UPDATE_GENOME_BROWSER = auto()
    UPDATE_LOCUSZOOM = auto()
    

class CacheSerializer(Enum):
    STRING = StringSerializer
    JSON = JsonSerializer
    PICKLE = PickleSerializer
    
class CacheTTL(Enum):
    """ Time to Live (TTL) options for caching; in seconds """
    DEFAULT = 3600 # 1 hr
    SHORT = 300 # 5 minutes
    DAY = 86400
    
class CacheNamespace(CaseInsensitiveEnum):
    """ cache namespaces """
    FILER = auto() # FILER endpoints
    FILER_EXTERNAL_API = auto() # external FILER API endpoints
    GENOMICS = auto() # genomics endpoints
    ADVP = auto() # advp endpoints
    VIEW = auto() # view redirect endpoints
    ROOT = auto() # root api