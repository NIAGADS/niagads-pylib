import logging
import json

from jsonschema import (
    Draft7Validator as DraftValidator,
    exceptions as jsExceptions,
    validators as jsValidators,
)
from typing import List

from niagads.utils.dict import print_dict
from niagads.utils.list import list_to_string

from niagads.json_validator.format_checkers import JSONSchemaFormatChecker

from niagads.json_validator.custom_validators import (
    case_insensitive_enum_validator,
    one_of_enum_validator,
)


class JSONValidator:
    """
    takes a meta data JSON object and runs validation against a JSON schema

    see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/
    for info on custom validators & format checkers
    """

    def __init__(self, json_obj, schema, debug: bool = False):
        self._debug = debug
        self.logger = logging.getLogger(__name__)

        self.__json = json.loads(json_obj) if isinstance(json_obj, str) else json_obj
        self.__schema = None
        self.__case_insensitive: bool = False
        self.__schema_validator = None
        self.__custom_validator_class = None

        self.__create_custom_validator()
        self.set_schema(schema)

    def get_schema_validator(self):
        return self.__schema_validator

    def normalize(self):
        """normalizes JSON object against the schema
        1. matches against enums and fixes case
        """
        if self.__json is None:
            raise ValueError(
                "Need to set or load JSON file before attempting to normalize"
            )

    def case_insensitive(self, enable: bool = True):
        self.__case_insensitive = enable

        # need to recreate the custom validators
        self.__create_custom_validator()
        self.__initialize_schema_validator()

    def set_json(self, obj):
        """
        set JSON to be validated; this allow applying the same schema
        to multiple JSON objects w/out revalidating the schema itself

        Args:
            json (str|dict): JSON object to be validated in object or string format
        """
        self.__json = json.loads(obj) if isinstance(obj, str) else obj

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
            if any(x in schema for x in ["[", "{"]):  # assume json
                self.__schema = json.loads(schema)
            else:  # assume file
                with open(schema, "r") as fh:
                    self.__schema = json.loads(fh.read())
                if self._debug:
                    self.logger.debug(
                        "Schema loaded from file "
                        + schema
                        + ": "
                        + print_dict(self.__schema, pretty=True)
                    )
        elif isinstance(schema, dict):  # already an object
            self.__schema = schema
        else:
            raise ValueError("Invalid value provided for `schema`:" + str(schema))

    def __create_custom_validator(self):
        """
        create custom Draft Validator by adding in all custom validators
        basically a wrapper for the DraftValidator
        """
        custom_validators = dict(DraftValidator.VALIDATORS)

        # add custom validators here
        # e.g., validators['is_positive']=is_positive
        # where is_positive is a function
        # see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/

        if self.__case_insensitive:
            custom_validators["enum"] = case_insensitive_enum_validator
            custom_validators["oneOf"] = case_insensitive_enum_validator
        else:
            custom_validators["oneOf"] = one_of_enum_validator 

        self.__custom_validator_class = jsValidators.create(
            meta_schema=DraftValidator.META_SCHEMA, validators=custom_validators
        )

    def __initialize_schema_validator(self):
        """
        initializes the schema validator, so schema check
        happens exactly once
        """
        self.__check_schema()
        self.__schema_validator = self.__custom_validator_class(
            self.__schema, format_checker=JSONSchemaFormatChecker
        )

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
        except jsExceptions.SchemaError as err:
            raise err

    def validation_error(self, errors: List[str], prefix=None):
        """
        raises a validation exception prepended by the message
        errors is an array of strings

        Args:
            prefix (str, optional): message to prepend
            errors (List[str]): list of validation errors in str format
        """

        message = list_to_string(errors, delim=" // ")
        if prefix:
            message = prefix + " - " + message

        raise jsExceptions.ValidationError(message)

    def __parse_validation_error(self, error: jsExceptions.ValidationError):
        """
        primarily to catch poorly formatted validation errors, incl:
            * present but empty required fields

        Args:
            error (ValidationError): the validation error
        """
        required_fields = (
            [f for f in self.__schema["required"]]
            if "required" in self.__schema
            else []
        )

        msg = error.message
        property_name = error.path.popleft() if error.path else None # file-level error -> None
        if "is not of type 'null'" in msg:
            msg = f"unexpected value; check for an error in a related field or set to an empty string (text/EXCEL) or `null` (json)"
        elif msg.startswith("None is not of type"):
            if property_name in required_fields:
                msg = f"required field cannot be empty / null"
            else:
                msg = f"optional field contains an empty string / null value; check for related fields - the value may be required to qualify other data"

        if property_name is not None:
            return {property_name: msg}
        return msg

    def run(self, fail_on_error=False):
        """
        Validate the JSON against the supplied json-schema

        Args:
            fail_on_error (bool, optional): fail on error.  Defaults to False.

        Returns:
            
            raise a ValidationError or return list of errors depending on fail_on_erro flag
        Raises
            jsonschema.exceptions.ValidationError
        """
        errors = [
            self.__parse_validation_error(e)
            for e in sorted(self.__schema_validator.iter_errors(self.__json), key=str)
        ]

        if errors and fail_on_error :
            self.validation_error(errors)

        return errors
