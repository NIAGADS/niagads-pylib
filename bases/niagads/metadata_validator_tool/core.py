#!/usr/bin/env python3
"""NIAGADS JSON Schema based metadata validation.

This tool allows the user to perform [JSON Schema](https://json-schema.org/)-based validation
of a sample or file manifest metadata file
arranged in tabular format (with a header row that has field names matching the validation schema).

The tool works for delimited text files (.tab, .csv., .txt) as well as excel
(.xls, .xlsx) files.

This tool can be run as a script or can also be imported as a module.  When run as a script,
results are piped to STDOUT unless the `--log` option is specified.
"""

import argparse
from enum import auto
import json
import logging
from os import path

from typing import List, Union

from niagads.arg_parser.core import case_insensitive_enum_type
from niagads.enums.core import CaseInsensitiveEnum
from niagads.logging_utils.core import LOG_FORMAT_STR, ExitOnExceptionHandler
from niagads.metadata_validator.core import (
    BiosourcePropertiesValidator,
    FileManifestValidator,
)
from niagads.string_utils.core import xstr
from niagads.sys_utils.core import print_args, verify_path


class MetadataValidatorType(CaseInsensitiveEnum):
    """Enum defining types of supported tabular metadata files.

    ```python
    BIOSOURCE_PROPERTIES = '''biosource properties file;
    a file that maps a sample or participant to descriptive properties
    (e.g., phenotype or material) or a ISA-TAB-like sample file'''

    FILE_MANIFEST = "file manifest or a sample-data-relationship (SDRF) file"
    ```
    """

    BIOSOURCE_PROPERTIES = auto()
    FILE_MANIFEST = auto()


def get_templated_schema_file(dir: str, template: str) -> str:
    """Verify that templated schema file `{schemaDir}/{vType}.json` exists.

    Args:
        path (str): path to directory containing schema file
        template (str): template name

    Raises:
        FileExistsError: if the schema file does not exist

    Returns:
        str: schema file name
    """

    schemaFile = (
        path.join(dir, f"{template}.json") if dir is not None else f"{template}.json"
    )
    if verify_path(schemaFile):
        return schemaFile
    else:
        raise FileNotFoundError(f"Schema file `{schemaFile}` does not exist.")


def get_templated_metadata_file(
    prefix: str,
    template: str,
    extensions: List[str] = ["xlsx", "xls", "txt", "csv", "tab"],
) -> str:
    """Find metadata file based on templated name `{prefix}{validator_type}.{ext}`.

    Args:
        path (str): file path; may include prefix/file pattern to match (e.g. /files/study1/experiment1-)
        template (str): template name
        extensions (List[str], optional): allowable file extensions. Defaults to ["xlsx", "xls", "txt", "csv", "tab"].

    Raises:
        FileNotFoundError: if metadata file does not exist

    Returns:
        str: metadata file name
    """
    fileRoot = f"{prefix}{template}" if prefix is not None else f"{template}"
    for ext in extensions:
        file = f"{fileRoot}.{ext}"
        if verify_path(file):
            return file

    raise FileNotFoundError(
        f"Metadata file matching template `{fileRoot}` not found with any of the expected extensions `{xstr(extensions)}`"
    )


def initialize_validator(
    file: str, schema: str, metadataType: MetadataValidatorType, idField: str = None
) -> Union[BiosourcePropertiesValidator, FileManifestValidator]:
    """Initialize and return a metadata validator.

    Args:
        file (str): metadata file name
        schema (str): JSONschema file name
        metadataType (MetadataValidatorType): type of metadata to be validated
        idField (str, optional): biosource id field in the metadata file; required for `BIOSOURCE_PROPERTIES` validation. Defaults to None.

    Raises:
        RuntimeError: if `metadataType == 'BIOSOURCE_PROPERTIES'` and no `idField` was provided
        ValueError: if invalid `metadataType` is specified

    Returns:
        Union[BiosourcePropertiesValidator, FileManifestValidator]: the validator object
    """
    try:
        if MetadataValidatorType(metadataType) == MetadataValidatorType.FILE_MANIFEST:
            validator = FileManifestValidator(file, schema)
            validator.load()
            return validator
        else:
            if idField is None:
                raise RuntimeError(
                    "Must specify biosource id field `idField` to validate a biosource (sample or participants) metadata file"
                )
            bsValidator = BiosourcePropertiesValidator(file, schema)
            bsValidator.set_biosource_id(idField, requireUnique=True)
            bsValidator.load()
            return bsValidator
    except KeyError:
        raise ValueError(
            f"Invalid `metadataType` : '{str(metadataType)}'.  Valid values are: {', '.join(MetadataValidatorType.list())}"
        )


def run(
    file: str,
    schema: str,
    metadataType: str,
    idField: str = None,
    failOnError: bool = False,
):
    """Run validation.

    Validator initialization fully encapsulated.  Returns validation result.

    Args:
        file (str): metadata file name
        schema (str): JSONschema file name
        metadataType (MetadataValidatorType): type of metadata to be validated
        idField (str, optional): biosource id field in the metadata file; required for `BIOSOURCE_PROPERTIES` valdiatoin. Defaults to None.
        failOnError (bool, optional): raise an exception on validation error if true, otherwise returns list of validation errors. Defaults to False.

    Returns:
        list: list of validation errors
    """
    validator = initialize_validator(file, schema, metadataType, idField)
    try:
        result = validator.run(failOnError=failOnError)
        return result
    except Exception as err:
        logger.error(err)


if __name__ == "__main__":
    print("running")
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--template",
        help="template name for schema; assumes also metadata file matches template pattern",
    )
    parser.add_argument(
        "--metadataFileType",
        help="type of metadata file",
        choices=MetadataValidatorType.list(),
        type=case_insensitive_enum_type(MetadataValidatorType),
        required=True,
    )
    parser.add_argument(
        "--log",
        help="log results to <metadataFile>.log; otherwise pipes to STDOUT",
        action="store_true",
    )
    parser.add_argument(
        "--failOnError",
        help="fail on first error; otherwise complete validation and generate a list of errors/warnings",
        action="store_true",
    )

    parser.add_argument(
        "--schemaDir",
        help="full path to directory containing schema files; if not specified assumes current working directory; required when `--template` is specified",
    )
    parser.add_argument(
        "--metadataFilePrefix",
        help="""full path and optional prefix for the templated metadata file; required when `--template` is specified; 
            e.g. /files/SA99914/TMP_SSA99914_D1_E2-; 
            if not specified assumes files are name `template.ext` 
            and located in current working directory""",
    )

    parser.add_argument(
        "--metadataFile",
        help="full path to metadata file; required when no template is specified",
    )
    parser.add_argument(
        "--schemaFile",
        help="full path to schema file;required when no template is specified",
    ),

    parser.add_argument(
        "--idField",
        help=f"Biosample or participant id field label; required if `--metadataType = {str(MetadataValidatorType.BIOSOURCE_PROPERTIES)}`",
    )

    args = parser.parse_args()

    if args.template and (args.schemaDir is None or args.metadataFilePrefix is None):
        parser.error("--template requires --schemaDir and --metadataFilePrefix")

    if args.template is None and (args.schemaFile is None or args.metadataFile is None):
        parser.error(
            "no `template` specified; --schemaFile and --metadataFile required"
        )

    if (
        args.metadataFileType == MetadataValidatorType.BIOSOURCE_PROPERTIES
        and args.idField is None
    ):
        parser.error(
            f"metadataFileType is set to {str(MetadataValidatorType.BIOSOURCE_PROPERTIES)}; --idField is required"
        )

    logger = None
    if args.log:
        logger = logging.getLogger(__name__)
        logging.basicConfig(
            handlers=[
                ExitOnExceptionHandler(
                    filename=f"{args.metadataFile}.log",
                    mode="w",
                    encoding="utf-8",
                )
            ],
            format=LOG_FORMAT_STR,
            level=logging.DEBUG,
        )
        logger.info(
            f"Running metadata validator with the following options : {print_args(args)}"
        )

    schemaFile = (
        get_templated_schema_file(args.schemaDir, args.template)
        if args.template
        else args.schemaFile
    )
    metadataFile = (
        get_templated_metadata_file(args.metadataFilePrefix, args.template)
        if args.template
        else args.metadataFile
    )

    result = run(
        metadataFile,
        schemaFile,
        args.metadataFileType,
        args.idField,
        args.failOnError,
    )

    if logger is not None:
        logger.info(f"Validation Status: {result}")
    else:  # pipe to STDOUT
        print(json.dumps(result))
