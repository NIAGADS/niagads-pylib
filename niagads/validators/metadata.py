import logging
from json import dumps as j_dumps

from jsonschema import exceptions as jsExceptions

from . import JSONValidator
from ..parsers import ExcelFileParser, CSVFileParser
from ..utils.sys import is_xlsx
from ..utils.string import xstr

class MetadataValidator:
    """
    validate 2-column CSV format metadata file, with field names in
    first column:
    
    field   value
    
    """
    def __init__(self, fileName:str, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self.__file = fileName
        self.__schema = schema
        self.__metadata = None

    
    def get_metadata_object(self, asString=False):
        """
        retrieve the parsed metadata

        Args:
            asString (bool, optional): _description_. Defaults to False.

        Returns:
            metadata as JSON or JSON str (`asString = True`)
            
        Raises:
            ValueError is metadata has not yet been loaded
        """
        if self.__metadata is None:
            raise ValueError("metadata object has not yet been loaded; please run `load` before accessing")
        return j_dumps(self.__metadata) if asString else self.__metadata
    
    
    def load(self, worksheet:str=None):
        """
        load the metadata from a file, if EXCEL file specify name of worksheet to be extracted
        and convert to JSON
        
        worksheet (str|int, optional): worksheet name or index, starting from 0. Required for EXCEL files only.
     
        Args:
            worksheet (str, optional): name of worksheet in EXCEL file to be validated. Defaults to None.
        """
        if is_xlsx(self.__file):
            parser = ExcelFileParser(self.__file)
            parser.strip()
            if worksheet is None:
                raise TypeError("Metadata file is of type `xlsx` (EXCEL); must supply name of the worksheet to load")
            self.__metadata = parser.worksheet_to_json(
                worksheet, transpose=True, returnStr=False, header=None, index_col=0)[0]            

        else:
            parser = CSVFileParser(self.__file)
            parser.strip()
            self.__metadata = parser.to_json(transpose=True, returnStr=False, header=None, index_col=0)[0]
    

    def set_schema(self, schema):
        """
        set schema

        Args:
            schema (str|obj): schema file name or object
        """
        self.__schema = schema


    def run(self, failOnError:bool=False):
        """
        run validation

        Args:
            failOnError (bool, optional): flag to fail on ValidationError. Defaults to False.

        Returns:
            boolean if JSON is valid,
            array of errors if invalid 
            
        Raises:
            jsonschema.exceptions.ValidationError if `failOnError` = True
        """
        validator = JSONValidator(self.__metadata, self.__schema, self._debug)
        return validator.run(failOnError)
    
        
class FileManifestValidator:
    """
    validate a file manifest in CSV format, with column names
    and 1 row per file
    
    also compares against list of samples / biosources to make sure
    all biosources are known
    """
    def __init__(self, fileName, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self.__schema = schema
        self.__file = fileName
        self.__metadata = None
        
    
    def get_metadata_object(self, asString=False):
        """
        retrieve the parsed metadata

        Args:
            asString (bool, optional): _description_. Defaults to False.

        Returns:
            metadata as JSON or JSON str (`asString = True`)
            
        Raises:
            ValueError is metadata has not yet been loaded
        """
        if self.__metadata is None:
            raise ValueError("metadata object has not yet been loaded; please run `load` before accessing")
        return j_dumps(self.__metadata) if asString else self.__metadata
    

    def load(self, worksheet:str=None):
        """
        load the metadata from a file, if EXCEL file specify name of worksheet to be extracted
        and convert to JSON
        
        worksheet (str|int, optional): worksheet name or index, starting from 0. Required for EXCEL files only.
     
        Args:
            worksheet (str, optional): name of worksheet in EXCEL file to be validated. Defaults to None.
        """
        if is_xlsx(self.__file):
            parser = ExcelFileParser(self.__file)
            if worksheet is None:
                raise TypeError("Metadata file is of type `xlsx` (EXCEL); must supply name of the worksheet to load")
            self.__metadata = parser.worksheet_to_json(
                worksheet, returnStr=False, header=0)

        else:
            parser = CSVFileParser(self.__file)
            self.__metadata = parser.to_json(returnStr=False, header=0)


    def run(self, failOnError:bool=False):
        """
        run validation on each row

        Args:
            failOnError (bool, optional): flag to fail on ValidationError. Defaults to False.

        Returns:
            array of {row#: validation result} pairs
            
        Raises:
            jsonschema.exceptions.ValidationError if `failOnError` = True
        """
        
        result = []
        validator = JSONValidator(None, self.__schema, self._debug)
        for index, row in enumerate(self.__metadata):
            validator.set_json(row)
            rowIsValid = validator.run()
            if not failOnError:
                result.append({index: rowIsValid})
            elif not bool(rowIsValid):
                validator.validation_error(rowIsValid, prefix="row " + xstr(index) + " - " + xstr(row))

        return result

class BiosourcePropertiesValidator:
    """
    validate biosource properties in a CSV format file, with column names
    and 1 row per sample or subject
    
    """
    def __init__(self, fileName, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self.__schema = schema
        self.__validator = None
        self.__file = fileName