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
    URLS = auto()

class ResponseFormat(CaseInsensitiveEnum):
    """ enum for allowable response / output formats"""
    JSON = auto()
    TEXT = auto()
    VCF = auto()
    BED = auto()
    
class ResponseView(CaseInsensitiveEnum):
    """ enum for allowable views """
    TABLE = auto()
    IGV_BROWSER = auto()
    DEFAULT = auto()
    
class RedirectEndpoint(str, Enum):
    TABLE = '/view/table'
    IGV_BROWSER = '/view/igvbrowser'
    
    @classmethod
    def from_view(cls, view: ResponseView):
        """ get the correct redirect endpoint given a view"""
        match view:
            case ResponseView.TABLE:
                return cls.TABLE
            case ResponseView.IGV_BROWSER:
                return cls.IGV_BROWSER
            case _:
                raise NotImplementedError(f'No endpoint implemented for view: {view.value}')
    
class Assembly(CaseInsensitiveEnum, Enum):
    """enum for genome builds"""
    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"
        
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        if value.lower() == 'hg19': return cls.GRCh37
        if value.lower() == 'hg38': return cls.GRCh38
        return super(Assembly, cls)._missing_(value)


# FIXME: is this really necessary? onRowSelect can be driven by the target view
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
    QUERY_CACHE = auto() # for server-side pagination, sorting, filtering
    
    
class CacheKeyQualifier(CaseInsensitiveEnum):
    PAGE = "pagination-page" 
    CURSOR = "pagination-cursor"
    RESULT_SIZE = "pagination-result-size"
    RAW = auto()
    QUERY_CACHE = auto()
    REQUEST_PARAMETERS = "request"
    
    def __str__(self):
        return f'_{self.value}'
    