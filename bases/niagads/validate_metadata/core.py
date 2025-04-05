"""validate_metadata

This script allows the user validate a sample or file manifest metadata file
arranged in tabular format (field names in columns, values in rows).  Results
are piped to STDOUT unless `--log` option is specified.

This tool accepts comma separated value files (.csv) as well as excel
(.xls, .xlsx) files.

This file can also be imported as a module and contains the following
functions:

    * initialize_biosource_validator - initializes a biosource validator, a Validator object
    * initialize_validator - generic initializer conditioned on type to return a Validator object
    * run - runs the validation on a Validator object
"""

import argparse
import sys
from typing import List, Optional, Union

from niagads.metadata_validator.core import (
    BiosourcePropertiesValidator,
    FileManifestValidator,
    MetadataFileType,
)
from pydantic import BaseModel


class Validator(BaseModel):
    """
    A validator and optional id list pair
    """

    validator: Union[BiosourcePropertiesValidator, FileManifestValidator]
    ids: Optional[List[str]] = None


def initialize_biosource_validator(file: str, schema: str, idField: str) -> Validator:
    """
    initialize a generic biosource metadata validator

    Args:
        metadata (str): metadata file name
        schema (str): schema file name
        idField (str): biosource id field in the metadata file

    Returns:
        BiosourceValidator: validator and extracted list of all biosource
            ids from the file
    """
    bsValidator = BiosourcePropertiesValidator(file, schema)
    bsValidator.set_biosource_id(idField, requireUnique=True)
    bsValidator.load()

    return Validator(validator=bsValidator, ids=bsValidator.get_biosource_ids())


def initialize_validator(
    file: str, schema: str, metadataType: MetadataFileType, idField: str = None
) -> Validator:
    if metadataType == MetadataFileType.FILE_MANIFEST:
        return Validator(validator=FileManifestValidator(file, schema))
    else:
        return initialize_biosource_validator(file, schema, idField, metadataType)


def run(validator: Validator, failOnError):
    validator.validator.load()
    return validator.validator.run(failOnError=failOnError)


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
    validator = initialize_validator(
        args.metadataFile, args.schemaFile, args.metadataTyupe, idField
    )
    run(validator, args.failOnError)
