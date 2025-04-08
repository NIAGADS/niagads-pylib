from enum import auto, StrEnum
from api.common.enums.base_enums import CaseInsensitiveEnum

class Databases(CaseInsensitiveEnum):
    GENOMICS = auto()
    CACHE = auto()
    METADATA = auto()
    
class DataStore(StrEnum):
    GENOMICS = auto()
    FILER = auto()
    SHARED = auto()
