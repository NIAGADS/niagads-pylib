from enum import Enum, StrEnum, auto
from aiocache.serializers import StringSerializer, JsonSerializer, PickleSerializer

class CacheSerializer(Enum):
    STRING = StringSerializer
    JSON = JsonSerializer
    PICKLE = PickleSerializer
    
class CacheTTL(Enum):
    """ Time to Live (TTL) options for caching; in seconds """
    DEFAULT = 3600 # 1 hr
    SHORT = 300 # 5 minutes
    DAY = 86400
    
class CacheNamespace(StrEnum):
    """ cache namespaces """
    FILER = auto() # FILER endpoints
    FILER_EXTERNAL_API = auto() # external FILER API endpoints
    GENOMICS = auto() # genomics endpoints
    ADVP = auto() # advp endpoints
    VIEW = auto() # view redirect endpoints
    ROOT = auto() # root api
    QUERY_CACHE = auto() # for server-side pagination, sorting, filtering
    
    
class CacheKeyQualifier(StrEnum):
    PAGE = "pagination-page" 
    CURSOR = "pagination-cursor"
    RESULT_SIZE = "pagination-result-size"
    RAW = auto()
    QUERY_CACHE = auto()
    REQUEST_PARAMETERS = "request"
    VIEW = "view_"
    
    def __str__(self):
        return f'_{self.value}'
    