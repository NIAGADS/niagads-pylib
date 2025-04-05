"""validate_metadata

This script allows the user validate a sample or file manifest metadata file
arranged in tabular format (field names in columns, values in rows).  Results
are piped to STDOUT unless `--log` option is specified.

This tool accepts comma separated value files (.csv) as well as excel
(.xls, .xlsx) files.

This file can also be imported as a module and contains the following
functions:

    * initialize_validator - returns an initialized BiosourcePropertiesValidator or FileManifestValidator
    * run - initializes a validator and runs the validaton
"""

import argparse
import json
import logging
import sys

from typing import Union

from niagads.logging_utils.core import LOG_FORMAT_STR, ExitOnExceptionHandler
from niagads.metadata_validator.core import (
    BiosourcePropertiesValidator,
    FileManifestValidator,
    MetadataFileType,
)
from niagads.sys_utils.core import print_args


def initialize_validator(
    file: str, schema: str, metadataType: MetadataFileType, idField: str = None
) -> Union[BiosourcePropertiesValidator, FileManifestValidator]:
    if metadataType == MetadataFileType.FILE_MANIFEST:
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


if __name__ == "main":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--metadataFile",
        help="full path to metadata file",
        required=True,
    )
    parser.add_argument(
        "--schemaFile",
        help="full path to schema file",
        required=True,
    ),
    parser.add_argument(
        "--metadataType",
        help="type of metadata file",
        choices=[list(MetadataFileType)],
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

    knownArgs, _ = parser.parse_known_args()
    if knownArgs.metadataType in [
        MetadataFileType.PARTICIPANT,
        MetadataFileType.SAMPLE,
    ]:
        parser.add_argument(
            "--idField",
            required=True,
            help="Biosample or participant id field label; required if --metadataType is `PARTICIPANT` or `SAMPLE`",
        )

    # only need to parse the args again if --help was not requested
    if "--help" not in sys.argv and "-h" not in sys.argv:
        args = parser.parse_args()

    idField = args.idField if "idField" in args else None

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

    result = run(
        args.metadataFile, args.schemaFile, args.metadataType, idField, args.failOnError
    )

    if logger is not None:
        logger.info(f"Validation Status: {result}")
    else:  # pipe to STDOUT
        print(json.dumps(result))
