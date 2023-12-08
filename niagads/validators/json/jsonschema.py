import logging
import json

from jsonschema import Draft7Validator as DraftValidator, exceptions as JSExceptions, validators as JSValidators

from ...utils.string import xstr
from ...utils.dict import print_dict
from ...utils.list import list_to_string

from format_checkers import FORMAT_CHECKER

class JSONValidator:
    """
    takes a meta data JSON object and runs validation against a JSON schema
    
    see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/
    for info on custom validators & format checkers
    """
    def __init__(self, jsonObj, schema, debug:bool=False):
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        
        self.__metadataJson = json.loads(jsonObj) if isinstance(jsonObj, str) else jsonObj 
        self.__schema = None
        self.__schemaValidator = None
        self.__customValidatorClass = None
        
        self.__create_custom_validator()
        self.set_schema(schema)
        
        
    def get_schema_validator(self):
        return self.__schemaValidator
        
        
    def set_schema(self, schema):
        """
        set the schema
        runs schema validation

        Args:
            schema (str | dict): jsonObj or string defining the schema or a file path
        """
        self.__load_schema(schema)
        self.__initialize_schema_validator()
        
        
    def __load_schema(self, schema):
        """
        schema may be passed as an object, json string, or file name
        if json string, parse
        if file, load from file

        Args:
            schema (str | dict): json schema as file, dict, or string
            
        Raises
            JSONDecodeError if invalid JSON string or invalid JSON loaded from file
            ValueError if neither object or string
            IOError if error reading file
        """
        if isinstance(schema, str):
            if any(x in schema for x in ['[', '{']): # assume json
                self.__schema = json.loads(schema)
            else: # assume file
                with open(schema, 'r') as fh:
                    self.__schema = json.loads(fh.read())   
                if self._debug:
                    self.logger.debug("Schema loaded from file " + schema + ": " + print_dict(self.__schema, pretty=True))
        elif isinstance(schema, dict): # already an object
            self.__schema = schema
        else:
            raise ValueError("Invalid value provided for `schema`:" + str(schema))


    def __create_custom_validator(self):
        """
        create custom Draft Validator by adding in all custom validators
        basically a wrapper for the DraftValidator
        """
        customValidators = dict(DraftValidator.VALIDATORS)
        # add custom validators here
        # e.g., validators['is_positive']=is_positive
        # where is_positive is a function 
        # see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/
        
        self.__customValidatorClass = JSValidators.create(meta_schema=DraftValidator.META_SCHEMA, validators=customValidators)
        
        
    def __initialize_schema_validator(self):
        """
        initializes the schema validator, so schema check 
        happens exactly once
        """
        self.__check_schema()      
        self.__schemaValidator = self.__customValidatorClass(self.__schema, format_checker=FORMAT_CHECKER)
        

    def __check_schema(self) -> bool:
        """
        make sure the schema itself is valid
        
        Returns:
            True if valid, raises error if not
        
        Raises:
            jsonschema.exceptions.SchemaError
        """
        try:
            DraftValidator.check_schema(self.__schema)
            return True
        except JSExceptions.SchemaError as err:
            raise err
        
        
    def run(self, failOnError=False):
        """
        Validate the JSON against the supplied json-schema

        Args:
            failOnError (bool, optional): fail on error.  Defaults to False.

        Returns:
            True if valid
            else raise a ValidationError or return list of errors depending on failOnError flag
        Raises
            jsonschema.exceptions.ValidationError
        """
        errors = [e.message for e in sorted(self.__schemaValidator.iter_errors(self.__metadataJson), key=str)]
        if len(errors) == 0:
            return True

        if failOnError:
            raise JSExceptions.ValidationError(list_to_string(errors, delim=" // "))

        else:
            return errors
    
