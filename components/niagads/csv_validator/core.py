import json
import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Union

import pandas as pd
from niagads.csv_parser.core import CSVFileParser
from niagads.excel_parser.core import ExcelFileParser
from niagads.json_validator.core import JSONValidator
from niagads.utils.list import drop_nulls
from niagads.utils.string import xstr
from niagads.utils.sys import is_xlsx


class CSVValidator(ABC):
    """
    Abstract Base Class for JSON-schema based CSV validation
    """

    def __init__(
        self,
        file_name: str,
        schema,
        case_insensitive: bool = False,
        debug: bool = False,
    ):
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self._file = file_name
        self._schema = schema
        self._metadata = None
        self._case_insensitive = case_insensitive

    def set_schema(self, schema):
        """
        set schema

        Args:
            schema (str|obj): schema file name or object
        """
        self._schema = schema

    def get_schema(self, as_json: bool=False):
        if as_json:
            return self.__parse_schema()
        return self._schema
    
    def __parse_schema(self):
        """
        Parse the schema from a dict, JSON string, or file path.

        Returns:
            dict: Parsed schema

        Raises:
            ValueError: If the schema is not in an expected format.
        """
        if isinstance(self._schema, str):
            if any(x in self._schema for x in ["[", "{"]):  # assume json
                return json.loads(self._schema)
            else:  # assume file
                with open(self._schema, "r") as fh:
                    return json.loads(fh.read())

        elif isinstance(self._schema, dict):  # already an object
            return self._schema
        else:
            raise ValueError("Invalid `schema` format:" + str(self._schema))
        
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
            raise ValueError(
                "metadata object has not yet been loaded; please run `load` before accessing"
            )
        return json.dumps(self._metadata) if asString else self._metadata

    @abstractmethod
    def load(self, worksheet: str = None):
        raise NotImplementedError(
            "`load` method has not been implement for the child of this Abstract parent class"
        )

    @abstractmethod
    def run(self, fail_on_error: bool = False):
        raise NotImplementedError(
            "`run` method has not been implement for the child of this Abstract parent class"
        )


class CSVPropertiesFileValidator(CSVValidator):
    """
    validate 2-column CSV format file using a JSON-schema,
    with field names in first column as follows:

    field   value

    no file header

    (e.g. study info files)
    """

    def __init__(self, file_name: str, schema, debug: bool = False):
        super().__init__(file_name, schema, debug)

    def load(self, worksheet: Union[str, int] = 0):
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
                raise TypeError(
                    "Metadata file is of type `xlsx` (EXCEL); must supply name of the worksheet to load"
                )
            self._metadata = parser.worksheet_to_json(
                worksheet, transpose=True, return_str=False, header=None, index_col=0
            )[0]

        else:
            parser = CSVFileParser(self._file)
            parser.strip()
            self._metadata = parser.to_json(
                transpose=True, return_str=False, header=None, index_col=0
            )[0]

    def run(self, fail_on_error: bool = False):
        """
        run validation

        Args:
            fail_on_error (bool, optional): flag to fail on ValidationError. Defaults to False.

        Returns:
            list of errors

        Raises:
            jsonschema.exceptions.ValidationError if `fail_on_error` = True
        """
        validator = JSONValidator(self._metadata, self._schema, self._debug)
        return validator.run(fail_on_error)


class CSVTableValidator(CSVValidator):
    """
    validate informtion organized in tabular format, with column names
    and 1 row per entity (e.g., sample files, sample-data-relationshp files, file manifests)
    to be validated

    """

    def __init__(
        self, file_name, schema, case_insensitive: bool = False, debug: bool = False
    ):
        super().__init__(file_name, schema, case_insensitive, debug)

    def get_field_values(self, field: str, drop_nulls: bool = False):
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
            raise TypeError(
                "metadata not loaded; run `[validator].load()` before extracting sample IDs"
            )

        if field not in self._metadata[0]:  # metadata is a list of dicts
            raise KeyError(f"invalid metadata field `{field}`; cannot extract values")

        field_values = [r[field] for r in self._metadata]
        return drop_nulls(field_values) if drop_nulls else field_values

    def load(self, worksheet: Union[str, int] = 0):
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
                raise TypeError(
                    "Metadata file is of type `xlsx` (EXCEL); must supply name of the worksheet to load"
                )
            self._metadata = parser.worksheet_to_json(
                worksheet, return_str=False, header=0
            )

        else:
            parser = CSVFileParser(self._file)
            self._metadata = parser.to_json(return_str=False, header=0)

    def to_text(self, path_or_buf: str = None, normalize: bool = False):
        """Write the metadata to tab-delimited text file"""
        metadata = self.normalize() if normalize else self._metadata
        df = pd.DataFrame(metadata)
        return df.to_csv(path_or_buf, sep="\t", index=False)


    def __resolve_enum_values(self, property_schema: dict):
        property_type = property_schema.get('type')
        if property_type == 'string' or (isinstance(property_type, list) and 'string' in property_type):
            if "enum" in property_schema:
                return property_schema["enum"], True
            if "oneOf" in property_schema:
                section = property_schema['oneOf']
                if section and all(isinstance(s, dict) and "const" in s and isinstance(s["const"], str) for s in section):
                    return [item["const"] for item in section]
        return []
            
    def normalize(self):
        """
        Get a normalized version of the metadata json, where normalization matches against enum
        fields and replaces values as necessary to match the canonical cases from the schema.
        """
        normalized_metadata = deepcopy(self._metadata)
        schema_json = self.get_schema(as_json=True)
        for record in normalized_metadata:
            for field, field_schema in schema_json.get("properties", {}).items():
                if field in record:
                    allowed_values = self.__resolve_enum_values(field_schema)
                    field_value = record[field]
                    if isinstance(field_value, str):
                        # find first case-insensitive match
                        canonical = next(
                            (
                                v
                                for v in allowed_values
                                if field_value.lower() == v.lower()
                            ),
                            None,
                        )
                        # only update if find a match
                        # leave mismatches as is for accurate error reporting
                        if canonical is not None:
                            record[field] = canonical
        return normalized_metadata

    def _resolve_file_level_errors(errors: dict[int, list[str]]):
        for row in errors:
            1    
        

    def run(self, fail_on_error: bool = False) -> dict:
        """
        run validation on each row

        Args:
            fail_on_error (bool, optional): flag to fail on ValidationError. Defaults to False.

        Returns:
            array of {row#: validation result} pairs

        Raises:
            jsonschema.exceptions.ValidationError if `fail_on_error` = True
        """
        
        INVALID_FIELD_ERRORS = ["Additional properties are not allowed", "is a required property"]
        
        file_errors = [] # for file-level errors
        result = []
        validator = JSONValidator(None, self._schema, self._debug)
        validator.case_insensitive(enable = self._case_insensitive)
        for index, row in enumerate(self._metadata):
            validator.set_json(row)
            row_errors = validator.run()
            if row_errors:
                if fail_on_error:
                    validator.validation_error(
                        row_errors, prefix="row " + xstr(index) + " - " + xstr(row)
                    )
                else:
                    filtered_row_errors = []
                    for err in row_errors:
                        if any(msg in err for msg in INVALID_FIELD_ERRORS):
                            file_errors.append(err)
                        else:
                            filtered_row_errors.append(err)
                    if filtered_row_errors:
                        result.append({index + 1: filtered_row_errors})
                    
        if file_errors:
            result.insert(0, {'file': list(set(file_errors))})

        return {"errors": result}  # empty array; all rows passed
