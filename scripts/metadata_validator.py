#! /usr/bin/env python3
import logging
import argparse
from os import path, getcwd
from typing import List

from niagads.utils.logging import ExitOnExceptionHandler
from niagads.validators import MetadataValidator, FileManifestValidator, BiosourcePropertiesValidator
from niagads.utils.dict import print_dict
from niagads.utils.list import list_to_string
from niagads.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

def initialize_biosource_validator(metadataType: str, idField:str):
    """
    initialize a generic biosource validator

    Args:
        metadataType (str): the metadataType so that the schema and metadata files can be identified
        sampleField (str): the name of the field containing the biosource identifier

    Returns:
        _type_: _description_
    """
    schemaFile = path.join(args.schemaDir, f'{metadataType}.json')
    metadataFile = path.join(args.metadataFileDir, f'{args.filePrefix}{metadataType}.{args.fileType}')
    log_start_validation(metadataType, metadataFile)
    
    bsValidator = BiosourcePropertiesValidator(metadataFile, schemaFile, args.debug)
    bsValidator.set_biosource_id(idField, requireUnique=True)
    bsValidator.load()
    
    log_parsed_metadata(bsValidator) # debugging
    
    return bsValidator, bsValidator.get_biosource_ids()


def validate_subject_info():
    """
    validates subject_info metadata file

    Returns:
        tuple of the validation result and the subject IDs so they can be used to validate the subjects in the sample_info file
    """
    subjectValidator, subjectIds = initialize_biosource_validator('subject_info', 'subject_id')
    validationResult = subjectValidator.run(failOnError=args.failAtFirst)
    result = "PASSED" if isinstance(validationResult, bool) else validationResult
    return result, subjectIds


def validate_sample_info(expectedSubjectIds: List[str]):
    """
    validates the sample_info metadata file

    Args:
        expectedSubjectIds (List[str]): subject ids expected from the subject_info_file

    Returns:
        tuple of the validation reuslt and the sample IDS so they can be used to validate the file manifest
    """
    sampleValidator, sampleIds = initialize_biosource_validator('sample_info', 'sample_id')
    validationResult = sampleValidator.run(failOnError=args.failAtFirst)
    result = [] if isinstance(validationResult, bool) else validationResult
    
    # Compare Subject IDS in the sample_info file to Expected Subject IDS from the subject_info file
    # Sample-Subject ID not in Expected Subject -> Error
    # Expected Subject missing from Sample-Subjects -> Warning
    
    # extract the subjectIds 
    subjectIds = sampleValidator.get_field_values('subject_id', dropNulls=True)
    expectedSet = set(expectedSubjectIds)
    sampleSet = set(subjectIds)
    
    missingExpectedSubjects = list(expectedSet - sampleSet)
    invalidSampleSubjects = list(sampleSet - expectedSet)
    
    if len(invalidSampleSubjects) > 0:
        error = ValidationError(f'Invalid subjects found in the sample file: {list_to_string(invalidSampleSubjects, delim=', ')}')
        if args.failAtFirst:
                raise error
        else:
            result.append(f'ERROR: {error.message}')

    if len(missingExpectedSubjects) > 0:
        message = f'WARNING: Expected subjects missing from the sample info file: {list_to_string(missingExpectedSubjects, delim=', ')}' 
        result.append(message)

    if len(result) == 0:
        result = "PASSED"

    return result, sampleIds


def validate_file_manifest(expectedSampleIds: List[str]):
    """
    validate the file manifest

    Args:
        sampleIds (List[str]): sample IDs expected from the sample_info file
        
    Returns:
        validation result
    """
    metadataType = 'file_manifest'
    schemaFile = path.join(args.schemaDir, f'{metadataType}.json')
    metadataFile = path.join(args.metadataFileDir, f'{args.filePrefix}{metadataType}.{args.fileType}')
    log_start_validation(metadataType, metadataFile)

    fmValidator = FileManifestValidator(metadataFile, schemaFile, args.debug)
    fmValidator.load()
    
    log_parsed_metadata(fmValidator) # debugging
        
    fmValidator.set_sample_reference(expectedSampleIds)
    validationResult = fmValidator.run(failOnError=args.failAtFirst)
    
    return "PASSED" if isinstance(validationResult, bool) else validationResult
    
    
def log_start_validation(metadataType, metadataFile):
    logger.info(f'Validating `{metadataType}` file: {metadataFile}')
    
    
def log_parsed_metadata(validator: MetadataValidator):
    logger.debug(print_dict(validator.get_metadata(), pretty=True))

    
def run():
    try:
        result = {}

        # Subjects
        validationResult, subjectIds = validate_subject_info()
        result['subject_info'] = validationResult

        # Samples
        validationResult, sampleIds = validate_sample_info(subjectIds)
        result['sample_info'] = validationResult
        
        # File Manifest
        validationResult = validate_file_manifest(sampleIds)
        result['file_manifest'] = validationResult
        
        logger.info("DONE")
        logger.info(print_dict(result, pretty=True))
        
    except Exception as err:
        logger.exception(err)


if __name__ == "__main__":
    argParser = argparse.ArgumentParser(description="EXCEL to JSON w/Validation test", allow_abbrev=False)
    argParser.add_argument('--metadataFileDir', help="full path to directory containing metadata files", required=True)
    argParser.add_argument('--schemaDir', help="full path to directory containing schema files", required=True)
    argParser.add_argument('--filePrefix', help="prefix to add to file names", default='')
    argParser.add_argument('--fileType', choices=['xlsx', 'tab'], help="file type; assuming `file type == fil extension`", default="tab")
    argParser.add_argument('--logFile', help="log file name (full path).  Default log saves to current working directory", 
        default="validation_test.log")
    argParser.add_argument('--failAtFirst', help="fail on first error; otherwise generatese a list of errors", action='store_true')
    argParser.add_argument('--debug', action='store_true')
    
    args = argParser.parse_args()

    logging.basicConfig(
            handlers=[ExitOnExceptionHandler(
                filename=path.join(getcwd(), args.logFile),
                mode='w',
                encoding='utf-8',
            )],
            format='%(asctime)s %(funcName)s %(levelname)-8s %(message)s',
            level=logging.DEBUG if args.debug else logging.INFO)
    
    run()
    
    
