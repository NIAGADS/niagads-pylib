import logging

from . import JSONValidator
from ..parsers.excel import ExcelFileParser

class MetadataValidator:
    """
    validate 2-column CSV format metadata file, with field names in
    first column:
    
    field   value
    
    """
    def __init__(self, fileName, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self.__schema = schema
        self.__validator = None
        self.__fileName = fileName
           
        
class FileManifestValidator:
    """
    validate a file manifest in CSV format, with column names
    and 1 row per file
    """
    def __init__(self, fileName, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self.__schema = schema
        self.__validator = None
        self.__fileName = fileName

class BiosourceValidator:
    """
    validate biosource properties in a CSV format file, with column names
    and 1 row per sample or subject
    
    """
    def __init__(self, fileName, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self.__schema = schema
        self.__validator = None
        self.__fileName = fileName