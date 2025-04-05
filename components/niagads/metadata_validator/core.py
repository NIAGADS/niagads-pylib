from enum import auto
from typing import List, Annotated

from niagads.csv_validator.core import CSVTableValidator
from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError
from niagads.list_utils.core import get_duplicates, list_to_string


class MetadataFileType(CaseInsensitiveEnum):
    """
    Types of tabular metadata files
    """

    PARTICIPANT: Annotated[str, "participant or subject file"] = auto()
    FILE_MANIFEST: Annotated[str, "file manifest; may map samples to files"] = auto()
    SAMPLE: Annotated[str, "sample biocharacteristics"] = auto()
    SDRF: Annotated[str, "sample-data-relationship file"] = auto()


class FileManifestValidator(CSVTableValidator):
    """
    validate a file manifest in CSV format, with column names
    and 1 row per file

    also compares against list of samples / biosources to make sure
    all biosources are known
    """

    def __init__(self, fileName, schema, debug: bool = False):
        self.__sampleReference: List[str] = None
        self.__sampleField: str = "sample_id"
        super().__init__(fileName, schema, debug)

    def set_sample_reference(self, sampleReference: List[str]):
        self.__sampleReference = sampleReference

    def set_sample_field(self, field: str):
        self.__sampleField = field

    def validate_samples(self, failOnError: bool = False):
        """
        verifies that samples in the file manifest are
        present in a reference list of samples

        Args:
            failOnError (bool, optional): fail on error; if False, returns list of errors.  Defaults to False.

        Returns:
            list of invalid samples
        """

        sampleIds = self.get_field_values(self.__sampleField, dropNulls=True)
        sampleSet = set(sampleIds)
        referenceSet = set(self.__sampleReference)

        invalidSamples = list(sampleSet - referenceSet)
        missingSamples = list(referenceSet - sampleSet)

        if len(invalidSamples) == 0 and len(missingSamples) == 0:
            return True

        messages = []
        if len(invalidSamples) > 0:
            error = ValidationError(
                "Invalid samples found: " + list_to_string(invalidSamples, delim=", ")
            )
            if failOnError:
                raise error
            else:
                messages.append(f"ERROR: {error.message}")

        if len(missingSamples) > 0:
            msg = "WARNING: Files not found for all samples: " + list_to_string(
                missingSamples, delim=", "
            )
            messages.append(msg)

        return messages

    def run(self, failOnError: bool = False):
        """
        run validation on each row

        wrapper of TableValidator.run that also does sample validation
        """
        result = super().run(failOnError)

        if self.__sampleReference is not None:
            sampleValidationResult = self.validate_samples(failOnError)
            if not isinstance(sampleValidationResult, bool):
                result = [] if isinstance(result, bool) else result
                if isinstance(result, list):
                    return result + sampleValidationResult
                else:
                    return [sampleValidationResult]

        return result


class BiosourcePropertiesValidator(CSVTableValidator):
    """
    validate biosource properties in a CSV format file, with column names
    and 1 row per sample or participant

    """

    def __init__(self, fileName, schema, debug: bool = False):
        super().__init__(fileName, schema, debug)
        self.__biosourceID = "sample_id"
        self.__requireUniqueIDs = False

    def set_biosource_id(self, idField: str, requireUnique: bool = False):
        self.__biosourceID = idField
        self.__requireUniqueIDs = requireUnique

    def require_unique_identifiers(self):
        self.__requireUniqueIDs = True

    def validate_unqiue_identifiers(self, failOnError: bool = False):
        duplicates = get_duplicates(self.get_biosource_ids())
        if len(duplicates) > 0:
            error = ValidationError(
                f'Duplicate biosource identifiers found: {list_to_string(duplicates, delim=", ")}'
            )
            if failOnError:
                raise error
            else:
                return f"ERROR: {error.message}"
        return True

    def get_biosource_ids(self):
        """
        extract biosource IDs
        """
        return self.get_field_values(self.__biosourceID)

    def run(self, failOnError: bool = False):
        """
        run validation on each row

        wrapper of TableValidator.riun that also does sample validation
        """
        result = super().run(failOnError)
        if self.__requireUniqueIDs:
            sampleValidationResult = self.validate_unqiue_identifiers(failOnError)
            if not isinstance(sampleValidationResult, bool):
                if isinstance(result, list):
                    return result + sampleValidationResult
                else:
                    return [sampleValidationResult]

        return result
