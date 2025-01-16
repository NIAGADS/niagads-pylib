import logging
from json import dumps as j_dumps
from abc import ABC, abstractmethod 

from typing import List, Set, Union

from jsonschema import exceptions as jsExceptions

from . import JSONValidator
from ..parsers import ExcelFileParser, CSVFileParser
from ..utils.sys import is_xlsx
from ..utils.string import xstr
from ..utils.list import list_to_string, get_duplicates
from ..utils.exceptions import ValidationError

class CSVValidator(ABC):
    """
    Abstract Base Class for JSON-schema based CSV validation
    """
    def __init__(self, fileName:str, schema, debug:bool=False):
        self._debug = debug
        self.logger  = logging.getLogger(__name__)
        self._file = fileName
        self._schema = schema
        self._metadata = None
    
    
    def set_schema(self, schema):
        """
        set schema

        Args:
            schema (str|obj): schema file name or object
        """
        self._schema = schema
        
        
    def get_schema(self):
        return self._schema
    
    def get_metadata(self, asString=False):
        """
        retrieve the parsed metadata

        Args:
            asString (bool, optional): _description_. Defaults to False.

        Returns:
            metadata as JSON or JSON str (`asString = True`)
            
        Raises:
            ValueError if metadata has not yet been loaded
        """
        if self._metadata is None:
            raise ValueError("metadata object has not yet been loaded; please run `load` before accessing")
        return j_dumps(self._metadata) if asString else self._metadata
    
    @abstractmethod
    def load(self, worksheet:str=None):
        raise NotImplementedError("`load` method has not been implement for the child of this Abstract parent class")
    
    @abstractmethod
    def run(self, failOnError:bool=False):
        raise NotImplementedError("`run` method has not been implement for the child of this Abstract parent class")
    
    
class MetadataValidator(CSVValidator):
    """
    validate 2-column CSV format metadata file using a JSON-schema,
    with field names in first column as follows:
    
    field   value
    
    no file header
    """
    def __init__(self, fileName:str, schema, debug:bool=False):
        super().__init__(fileName, schema, debug)

    def load(self, worksheet:Union[str, int]='Sheet1'):
        """
        load the metadata from a file, if EXCEL file specify name of worksheet to be extracted
        and convert to JSON
    
        Args:
            worksheet (str|int, optional): name or zero-based index of worksheet in EXCEL file to be validated. Required for EXCEL files only.  Defaults to 'Sheet1'.
        """
        if is_xlsx(self._file):
            parser = ExcelFileParser(self._file)
            parser.strip()
            if worksheet is None:
                raise TypeError("Metadata file is of type `xlsx` (EXCEL); must supply name of the worksheet to load")
            self._metadata = parser.worksheet_to_json(
                worksheet, transpose=True, returnStr=False, header=None, index_col=0)[0]            

        else:
            parser = CSVFileParser(self._file)
            parser.strip()
            self._metadata = parser.to_json(transpose=True, returnStr=False, header=None, index_col=0)[0]
    
    
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
        validator = JSONValidator(self._metadata, self._schema, self._debug)
        return validator.run(failOnError)
    
        
class TableValidator(CSVValidator):
    """
    validate metadata organized in CSV format, with column names
    and 1 row per entity (e.g., file or biosource properties) 
    to be validated

    """
    def __init__(self, fileName, schema, debug:bool=False):
        super().__init__(fileName, schema, debug)
        
    def load(self, worksheet:str=None):
        """
        load the metadata from a file, if EXCEL file specify name of worksheet to be extracted
        and convert to JSON
        
        worksheet (str|int, optional): worksheet name or index, starting from 0. Required for EXCEL files only.

        Args:
            worksheet (str, optional): name of worksheet in EXCEL file to be validated. Defaults to None.
        """
        if is_xlsx(self._file):
            parser = ExcelFileParser(self._file)
            if worksheet is None:
                raise TypeError("Metadata file is of type `xlsx` (EXCEL); must supply name of the worksheet to load")
            self._metadata = parser.worksheet_to_json(worksheet, returnStr=False, header=0)

        else:
            parser = CSVFileParser(self._file)
            self._metadata = parser.to_json(returnStr=False, header=0)
            
            
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
        validator = JSONValidator(None, self._schema, self._debug)
        for index, row in enumerate(self._metadata):
            validator.set_json(row)
            rowValidation = validator.run()
            if not isinstance(rowValidation, bool):
                if failOnError:
                    validator.validation_error(rowValidation, prefix="row " + xstr(index) + " - " + xstr(row))
                else:
                    result.append({index: rowValidation})
        
        return True if len(result) == 0 else result # empty array; all rows passed
        
        
class FileManifestValidator(TableValidator):
    """
    validate a file manifest in CSV format, with column names
    and 1 row per file
    
    also compares against list of samples / biosources to make sure
    all biosources are known
    """
    def __init__(self, fileName, schema, debug:bool=False):
        self.__sampleReference: List[str] = None
        self.__sampleField: str = 'sample_id'
        super().__init__(fileName, schema, debug)
        
    
    def set_sample_reference(self, sampleReference:List[str]):
        self.__sampleReference = sampleReference
        
        
    def set_sample_field(self, field:str):
        self.__sampleField = field
        
        
    def validate_samples(self, failOnError:bool=False):
        """
        verifies that samples in the file manifest are 
        present in a reference list of samples

        Args:
            failOnError (bool, optional): fail on error; if False, returns list of errors.  Defaults to False.

        Returns:
            list of invalid samples
        """
        
        sampleSet = { r[self.__sampleField] for r in self._metadata }
        referenceSet  = set(self.__sampleReference)
    
        if referenceSet.issuperset(sampleSet):
            return True
        else:
            invalidSamples = list(sampleSet.difference(referenceSet))
            
            error = ValidationError("invalid samples found in file manifest: " + list_to_string(invalidSamples, delim=', '))
            if failOnError:
                raise error
            else:
                return error.message          



    def run(self, failOnError:bool=False):
        """
        run validation on each row

        wrapper of TableValidator.riun that also does sample validation
        """
        result = super().run(failOnError)
        if self.__sampleReference is not None:
            sampleValidationResult = self.validate_samples(failOnError)
            if isinstance(sampleValidationResult, list):
                if isinstance(result, list):
                    return result + [sampleValidationResult]
                else:
                    return [sampleValidationResult]
        
        return result        
            

class BiosourcePropertiesValidator(TableValidator):
    """
    validate biosource properties in a CSV format file, with column names
    and 1 row per sample or subject
    
    """
    def __init__(self, fileName, schema, debug:bool=False):
        super().__init__(fileName, schema, debug)
        self.__biosourceID = 'sample_id'
        self.__requireUniqueIDs = False
    
    def set_biosource_id(self, idField: str, requireUnique: bool=False):
        self.__biosourceID = idField
        self.__requireUniqueIDs = requireUnique
        

    def require_unique_identifiers(self):
        self.__requireUniqueIDs = True

        
    def validate_unqiue_identifiers(self, failOnError:bool=False):
        duplicates = get_duplicates(self.get_biosource_ids())
        if len(duplicates) > 0:
            error = ValidationError(f'Duplicate biosource identifiers found in the metadata file (n = {len(duplicates)}): {list_to_string(duplicates, delim=', ')}')
            if failOnError:
                raise error
            else:
                return error.message          
        return True
        
    
    def get_biosource_ids(self):
        """
        extract biosource IDs
        """
        if self._metadata is None:
            raise TypeError("metadata not loaded; run `.load` before extracting sample IDs")
        
        return [ r[self.__biosourceID] for r in self._metadata ] 
    
    
    def run(self, failOnError:bool=False):
        """
        run validation on each row

        wrapper of TableValidator.riun that also does sample validation
        """
        result = super().run(failOnError)
        if self.__requireUniqueIDs is not None:
            sampleValidationResult = self.validate_unqiue_identifiers(failOnError)
            if isinstance(sampleValidationResult, list):
                if isinstance(result, list):
                    return result + [sampleValidationResult]
                else:
                    return [sampleValidationResult]
        
        return result        
    
    