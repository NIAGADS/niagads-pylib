import logging
from json import dumps as j_dumps
from abc import ABC, abstractmethod 

from typing import List, Union

from jsonschema import exceptions as jsExceptions

from . import JSONValidator
from ..parsers import ExcelFileParser, CSVFileParser
from ..utils.sys import is_xlsx
from ..utils.string import xstr
from ..utils.list import drop_nulls, list_to_string, get_duplicates
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

    def load(self, worksheet:Union[str, int]=0):
        """
        load the metadata from a file, if EXCEL file specify name of worksheet to be extracted
        and convert to JSON
    
        Args:
            worksheet (str|int, optional): name or zero-based index of worksheet in EXCEL file to be validated. Required for EXCEL files only.  Defaults to the first sheet.
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
        
        
    def get_field_values(self, field: str, dropNulls: bool=False):
        """
        fetch all values in a table field

        Args:
            field (str): field name
            dropNulls (bool, Optional): drop null values from return. Defaults to False.

        Raises:
            TypeError: NullValue error if the metadata is not loaded
            KeyError: if the field does not exist in the table

        Returns:
            list of values in the field
        """
        
        if self._metadata is None:
            raise TypeError("metadata not loaded; run `[validator].load()` before extracting sample IDs")
        
        if field not in self._metadata[0]: # metadata is a list of dicts
            raise KeyError(f'invalid metadata field `{field}`; cannot extract values')
        
        fieldValues = [ r[field] for r in self._metadata ] 
        return drop_nulls(fieldValues) if dropNulls \
            else fieldValues
    
        
    def load(self, worksheet:Union[str, int]=0):
        """
        load the metadata from a file, if EXCEL file specify name of worksheet to be extracted
        and convert to JSON
        
        worksheet (str|int, optional): worksheet name or index, starting from 0. Required for EXCEL files only. Defaults to first sheet.

        Args:
            worksheet (str, optional): name of worksheet in EXCEL file to be validated. Defaults to first sheet.
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
                    result.append({index + 1: rowValidation})
        
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
        
        sampleIds = self.get_field_values(self.__sampleField, dropNulls=True)
        sampleSet = set(sampleIds)
        referenceSet  = set(self.__sampleReference)
        
        invalidSamples = list(sampleSet - referenceSet)
        missingSamples = list(referenceSet - sampleSet)
        
        if len(invalidSamples) == 0 and len(missingSamples) == 0:
            return True
        
        messages = []
        if len(invalidSamples) > 0:
            error = ValidationError("Invalid samples found: " + list_to_string(invalidSamples, delim=', '))
            if failOnError:
                raise error
            else:
                messages.append(f'ERROR: {error.message}')
                
        if len(missingSamples) > 0:
            msg = "WARNING: Files not found for all samples: " + list_to_string(missingSamples, delim=', ')
            messages.append(msg)
        
        return messages


    def run(self, failOnError:bool=False):
        """
        run validation on each row

        wrapper of TableValidator.run that also does sample validation
        """
        result = super().run(failOnError)
        
        if self.__sampleReference is not None:
            sampleValidationResult = self.validate_samples(failOnError)
            if not isinstance(sampleValidationResult, bool):
                result = [] if isinstance(result, bool) else result
                if isinstance(result, list):
                    return result + sampleValidationResult
                else:
                    return [sampleValidationResult]
        
        return result        
            

class BiosourcePropertiesValidator(TableValidator):
    """
    validate biosource properties in a CSV format file, with column names
    and 1 row per sample or participant
    
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
            error = ValidationError(f'Duplicate biosource identifiers found: {list_to_string(duplicates, delim=", ")}')
            if failOnError:
                raise error
            else:
                return f'ERROR: {error.message}'
        return True
        
    
    def get_biosource_ids(self):
        """
        extract biosource IDs
        """
        return self.get_field_values(self.__biosourceID)
    
    
    def run(self, failOnError:bool=False):
        """
        run validation on each row

        wrapper of TableValidator.riun that also does sample validation
        """
        result = super().run(failOnError)
        if self.__requireUniqueIDs:
            sampleValidationResult = self.validate_unqiue_identifiers(failOnError)
            if not isinstance(sampleValidationResult, bool):
                if isinstance(result, list):
                    return result + sampleValidationResult
                else:
                    return [sampleValidationResult]
        
        return result        
    
    