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
            boolean if JSON is valid,
            array of errors if invalid

        Raises:
            jsonschema.exceptions.ValidationError if `fail_on_error` = True
        """
        validator = JSONValidator(self._metadata, self._schema, self._debug)
        result = validator.run(fail_on_error)


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

    def to_text(self, normalize: bool = False):
        """Write the metadata to tab-delimited text file"""
        metadata = self.normalize() if normalize else self._metadata
        df = pd.DataFrame(metadata)
        return df.to_csv(sep="\t", index=False)

    def normalize(self):
        """
        Get a normalized version of the metadata json, where normalization matches against enum
        fields and replaces values as necessary to match the canonical cases from the schema.
        """
        normalized_metadata = deepcopy(self._metadata)
        for record in normalized_metadata:
            for field, field_schema in self._schema.get("properties", {}).items():
                if "enum" in field_schema and field in record:
                    value = record[field]
                    if isinstance(value, str):
                        # find first case-insensitive match
                        canonical = next(
                            (
                                e
                                for e in field_schema["enum"]
                                if value.lower() == e.lower()
                            ),
                            None,
                        )
                        # only update if find a match
                        # leave mismatches as is for accurate error reporting
                        if canonical is not None:
                            record[field] = canonical
        return normalized_metadata

    def run(self, fail_on_error: bool = False) -> dict:
        """
        run validation on each row

        Args:
            fail_on_error (bool, optional): flag to fail on ValidationError. Defaults to False.

        Returns:
            array of {row#: validation result} pairs

        Raises:
            jsonschema.exceptions.ValidationError if `failOnError` = True
        """

        result = []
        validator = JSONValidator(None, self._schema, self._debug)
        validator.case_insensitive(self._case_insensitive)
        for index, row in enumerate(self._metadata):
            validator.set_json(row)
            row_validation = validator.run()
            if not isinstance(row_validation, bool):
                if fail_on_error:
                    validator.validation_error(
                        row_validation, prefix="row " + xstr(index) + " - " + xstr(row)
                    )
                else:
                    result.append({index + 1: row_validation})

        return {"errors": result}  # empty array; all rows passed
