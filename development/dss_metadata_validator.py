#! /usr/bin/env python3
"""dss_metadata_validator

This script allows the user validate a sample or file manifest metadata file
arranged in tabular format (field names in columns, values in rows) against a JSON-Schema file.
Results are piped to STDOUT.

This tool accepts tab separated value files (.tab) as well as excel
(.xls, .xlsx) files.
"""
import argparse
import json
from typing import List

import niagads.validate_metadata.core as vm


def validate_participant_info():
    """
    validates participant_info metadata file

    Returns:
        validation result if args.participantsOnly, otherwise
        tuple of the validation result and the participant IDs so they can be used to validate the participants in the sample_info file
    """
    schema = vm.get_templated_schema_file(args.schemaDir, "participant_info")
    file = vm.get_templated_metadata_file(args.metadataFilePrefix, "participant_info")

    if args.participantsOnly:
        return vm.run(file, schema, "biosource_properties", "participant_id")
    else:
        pValidator = vm.initialize_validator(
            file, schema, "biosource_properties", "participant_id"
        )
        result = pValidator.run(failOnError=False)
        return result, pValidator.get_biosource_ids()


def validate_sample_info(expectedParticipantIds: List[str]):
    """
    validates the sample_info metadata file

    Args:
        expectedParticipantIds (List[str]): participant ids expected from the participant_info_file

    Returns:
        tuple of the validation reuslt and the sample IDS so they can be used to validate the file manifest
    """
    schema = vm.get_templated_schema_file(args.schemaDir, "sample_info")
    file = vm.get_templated_metadata_file(args.metadataFilePrefix, "sample_info")

    sValidator = vm.initialize_validator(
        file, schema, "biosource_properties", "sample_id"
    )
    result = sValidator.run(failOnError=False)

    # Compare Participant IDS in the sample_info file to Expected Participant IDS from the participant_info file
    # Sample-Participant ID not in Expected Participant -> Error
    # Expected Participant missing from Sample-Participants -> Warning

    # extract the participantIds
    participantIds = sValidator.get_field_values("participant_id", dropNulls=True)
    expectedSet = set(expectedParticipantIds)
    sampleSet = set(participantIds)

    missingExpectedParticipants = list(expectedSet - sampleSet)
    invalidSampleParticipants = list(sampleSet - expectedSet)

    if len(invalidSampleParticipants) > 0:
        result["errors"].append({"invalid_PARTICIPANT_ID": invalidSampleParticipants})

    if len(missingExpectedParticipants) > 0:
        warning = {"missing_PARTICIPANT_ID": missingExpectedParticipants}
        if "warnings" in result:
            result["warnings"].append(warning)
        else:
            result["warnings"] = [warning]

    return result, sValidator.get_biosource_ids()


def validate_file_manifest(expectedSampleIds: List[str] = None):
    """
    validate the file manifest

    Args:
        expectedSampleIds (List[str], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    schema = vm.get_templated_schema_file(args.schemaDir, "file_manifest")
    file = vm.get_templated_metadata_file(args.metadataFilePrefix, "file_manifest")

    if args.manifestOnly:
        # run a straight JSON schema validation
        return vm.run(file, schema, "file_manifest")
    else:
        # JSON schema validation and check that all reference samples and present in the sample_info file
        fmValidator = vm.initialize_validator(file, schema, "file_manifest")
        fmValidator.set_sample_field("sample_id")
        fmValidator.set_sample_reference(expectedSampleIds)
        result = fmValidator.run(failOnError=False)
        return result


def run():
    result = {}

    # Participants
    validationResult, participantIds = validate_participant_info()
    result["participant_info"] = validationResult

    # Samples
    validationResult, sampleIds = validate_sample_info(participantIds)
    result["sample_info"] = validationResult

    # File Manifest
    validationResult = validate_file_manifest(sampleIds)
    result["file_manifest"] = validationResult

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)

    parser.add_argument(
        "--schemaDir",
        help="full path to directory containing schema files",
        required=True,
    )
    parser.add_argument(
        "--manifestOnly", help="validate file manifest only", action="store_true"
    )
    parser.add_argument(
        "--participantsOnly", help="validate participant info only", action="store_true"
    )
    parser.add_argument(
        "--metadataFilePrefix",
        help="full path and prefix for the files e.g. /files/SA99914/TMP_SSA99914_D1_E2-",
        required=True,
    )

    args = parser.parse_args()

    if args.manifestOnly:
        result = validate_file_manifest()

    else:
        result = run()

    print(json.dumps(result))
