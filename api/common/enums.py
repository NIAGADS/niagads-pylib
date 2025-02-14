from enum import auto, Enum
from fastapi.exceptions import RequestValidationError
from aiocache.serializers import StringSerializer, JsonSerializer, PickleSerializer

from niagads.utils.enums import CustomStrEnum as StrEnum
from api.common.formatters import clean, print_enum_values

class CaseInsensitiveEnum(StrEnum):
    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        for member in cls:
            if member.value.lower() == value.lower(): 
                return member
    
        raise KeyError(value)
    
class EnumParameter(CaseInsensitiveEnum):
    @classmethod
    def exclude(cls, name, exclude):
        return EnumParameter(name, { member.name: member.value for member in cls if member not in exclude })

    @classmethod
    def get_description(cls):
        return f'One of: {print_enum_values(cls)}.'
    
    @classmethod
    def validate(cls, value, label: str, returnCls: Enum):
        try:
            cls(clean(value))
            return returnCls(value)
        except:
            raise RequestValidationError(f'Invalid value provided for `{label}`: {value}.  Allowable values for this query are: {print_enum_values(cls)}' )

    
class ResponseContent(EnumParameter):
    """ enum for allowable response types """
    FULL = auto()
    COUNTS = auto()
    IDS = auto()
    SUMMARY = auto()
    URLS = auto()
    
    @classmethod
    def get_description(cls, inclValues=True):
        message = 'Type of information returned by the query.'    
        return message + f' {super().get_description()}' if inclValues else message
    
    @classmethod
    def descriptive(cls, inclUrls=False, description=False):
        """ return descriptive formats only (usually for metadata)"""
        exclude = [ResponseContent.IDS, ResponseContent.COUNTS] if inclUrls \
            else [ResponseContent.IDS, ResponseContent.URLS, ResponseContent.COUNTS]
        subset = cls.exclude('descriptive_only_content', exclude )
        if description:
            return cls.get_description(False) + ' ' + subset.get_description()
        else:
            return subset
        
    @classmethod
    def data(cls, description=False):
        """ return data formats only"""
        subset = cls.exclude('descriptive_only_content', [ResponseContent.IDS, ResponseContent.URLS] )
        if description:
            return cls.get_description(False) + ' ' + subset.get_description()
        else:
            return subset
        

class ResponseFormat(EnumParameter):
    """ enum for allowable response / output formats"""
    JSON = auto()
    TEXT = auto()
    VCF = auto()
    BED = auto()
    
    @classmethod
    def get_description(cls, inclValues=True):
        message = 'Response format.  If a non-text `view` is specified, the response format will default to `JSON`'    
        return message + f' {super().get_description()}' if inclValues else message
    
    @classmethod
    def generic(cls, description=False):
        subset = cls.exclude('generic_formats', [ResponseFormat.VCF, ResponseFormat.BED] )
        if description:
            return cls.get_description(False) + ' ' + subset.get_description()
        else:
            return subset
    
    @classmethod
    def functional_genomics(cls, description=False):
        subset = cls.exclude('functional_genomics_formats', [ResponseFormat.VCF] )
        if description:
            return cls.get_description(False) + ' ' + subset.get_description()
        else:
            return subset

    
class ResponseView(EnumParameter):
    """ enum for allowable views """
    TABLE = auto()
    IGV_BROWSER = auto()
    DEFAULT = auto()
    
    @classmethod
    def get_description(cls, inclValues=True):
        message = 'Visual representation of the data.  Select `DEFAULT` for TEXT or JSON response.'    
        return message + f' {super().get_description()}' if inclValues else message
    
    @classmethod
    def table(cls, description=False):
        subset = cls.exclude('table_views', [ResponseView.IGV_BROWSER] )
        if description:
            return cls.get_description(False) + ' ' + subset.get_description()
        else:
            return subset
        
    
class Assembly(EnumParameter):
    """enum for genome builds"""
    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"
        
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        if value.lower() == 'hg19': return cls.GRCh37
        if value.lower() == 'hg38': return cls.GRCh38
        return super(Assembly, cls)._missing_(value)


# FIXME: is this really necessary? onRowSelect can be driven by the target view
class OnRowSelect(StrEnum):
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
    
class RecordType(CaseInsensitiveEnum):
    TRACK = auto()
    GENE = auto()
    VARIANT = auto()
    COLLECTION = auto()
    