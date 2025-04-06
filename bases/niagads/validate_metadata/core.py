#!/usr/bin/env python3
"""validate_metadata

This script allows the user validate a sample or file manifest metadata file
arranged in tabular format (field names in columns, values in rows) against a JSON-Schema file.
Results are piped to STDOUT unless `--log` option is specified.

This tool accepts tab separated value files (.tab) as well as excel
(.xls, .xlsx) files.

This file can also be imported as a module and contains the following
functions / tyes:

    * MetadataValidatorType - enum of types of expected metadata files
    * initialize_validator - returns an initialized BiosourcePropertiesValidator or FileManifestValidator
    * get_templated_schema_file - builds schema file name and verifies that file exists
    * get_templated_metadata_file - builds metadata file name and verifies that file exists
    * run - initializes a validator and runs the validaton
"""

import argparse
from enum import auto
import json
import logging
from os import path
import sys

from typing import Annotated, List, Union

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
    """
    Types of tabular metadata files
    """

    BIOSOURCE_PROPERTIES: Annotated[
        str,
        "biosource properties files, maps a sample or participant to descriptive properties (e.g., phenotype or material)",
    ] = auto()
    FILE_MANIFEST: Annotated[str, "file manifest"] = auto()
    # SDRF: Annotated[str, "sample-data-relationship file"] = auto()


def get_templated_schema_file(path: str, template: str) -> str:
    """
    verify that templated schema file ${schemaDir}/{vType}.json exists

    Args:
        path (str): path to directory containing schema file
        template (str): template name

    Raises:
        FileExistsError: if the schema file does not exist

    Returns:
        str: schema file name
    """

    schemaFile = (
        path.join(path, f"{template}.json") if path is not None else f"{template}.json"
    )
    if verify_path(schemaFile):
        return schemaFile
    else:
        raise FileNotFoundError(f"Schema file `{schemaFile}` does not exist.")


def get_templated_metadata_file(
    path: str,
    template: str,
    extensions: List[str] = ["xlsx", "xls", "txt", "csv", "tab"],
) -> str:
    """
    find metadata file based on templated name {prefix}{validator_type}.{ext}

    Args:
        path (str): file path; may include prefix/file pattern to match (e.g. /files/study1/experiment1-)
        template (str): template name
        extensions (List[str], optional): allowable file extensions. Defaults to ["xlsx", "xls", "txt", "csv", "tab"].

    Raises:
        FileNotFoundError: if metadata file does not exist

    Returns:
        str: metadata file name
    """
    fileRoot = f"{path}{template}" if path is not None else f"{template}"
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
    if metadataType == MetadataValidatorType.FILE_MANIFEST:
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


def run(
    file: str,
    schema: str,
    metadataType: str,
    idField: str = None,
    failOnError: bool = False,
):
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
        args.metadataFile,
        args.schemaFile,
        args.metadataFileType,
        args.idField,
        args.failOnError,
    )

    if logger is not None:
        logger.info(f"Validation Status: {result}")
    else:  # pipe to STDOUT
        print(json.dumps(result))
