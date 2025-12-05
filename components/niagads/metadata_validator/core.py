from typing import List

from niagads.csv_validator.core import CSVTableValidator
from niagads.exceptions.core import ValidationError
from niagads.utils.list import get_duplicates, list_to_string


class FileManifestValidator(CSVTableValidator):
    """
    validate a file manifest in CSV format, with column names
    and 1 row per file

    also compares against list of samples / biosources to make sure
    all biosources are known
    """

    def __init__(
        self, file_name, schema, case_insensitive: bool = False, debug: bool = False
    ):
        self.__sample_reference: List[str] = None
        self.__sample_field: str = "sample_id"
        super().__init__(file_name, schema, case_insensitive, debug)

    def set_sample_reference(self, samples: List[str]):
        self.__sample_reference = samples

    def set_sample_field(self, field: str):
        self.__sample_field = field

    def validate_samples(self, validation_result: dict, fail_on_error: bool = False):
        """
        verifies that samples in the file manifest are
        present in a reference list of samples

        Args:
            validation_result (dict): validation result to be updated
            fail_on_error (bool, optional): fail on error; if False, returns list of errors.  Defaults to False.

        Returns:
            updated validation result
        """

        sample_ids = self.get_field_values(self.__sample_field, drop_nulls=True)
        sample_set = set(sample_ids)
        reference_set = set(self.__sample_reference)

        invalid_samples = list(sample_set - reference_set)
        missing_samples = list(reference_set - sample_set)

        if len(invalid_samples) > 0:
            error = ValidationError(
                "Invalid samples found: " + list_to_string(invalid_samples, delim=", ")
            )
            if fail_on_error:
                raise error
            else:
                validation_result["errors"].append(
                    {f"invalid_{self.__sample_field.upper()}": invalid_samples}
                )

        if len(missing_samples) > 0:
            warning = {f"no_file_for_{self.__sample_field.upper()}": missing_samples}
            if "warnings" in validation_result:
                validation_result["warnings"].append(warning)
            else:
                validation_result["warnings"] = [warning]

        return validation_result

    def run(self, fail_on_error: bool = False):
        """
        run validation on each row

        wrapper of TableValidator.run that also does sample validation
        """
        result = super().run(fail_on_error)

        if self.__sample_reference is not None:
            result = self.validate_samples(result, fail_on_error)

        return result


class BiosourcePropertiesValidator(CSVTableValidator):
    """
    validate biosource properties in a CSV format file, with column names
    and 1 row per sample or participant

    """

    def __init__(
        self, file_name, schema, case_insensitive: bool = False, debug: bool = False
    ):
        super().__init__(file_name, schema, case_insensitive, debug)
        self._biosource_id = "sample_id"
        self.__require_unique_ids = False

    def set_biosource_id(self, field: str, must_be_unique: bool = False):
        self._biosource_id = field
        self.__require_unique_ids = must_be_unique

    def require_unique_identifiers(self):
        self.__require_unique_ids = True

    def validate_unqiue_identifiers(
        self, validation_result: dict, fail_on_error: bool = False
    ):
        duplicates = get_duplicates(self.get_biosource_ids())
        if len(duplicates) > 0:
            error = ValidationError(
                f'Duplicate biosource identifiers found: {list_to_string(duplicates, delim=", ")}'
            )
            if fail_on_error:
                raise error
            else:
                validation_result["errors"].append(
                    {f"duplicate_{self._biosource_id.upper()}": duplicates}
                )
        return validation_result

    def get_biosource_ids(self):
        """
        extract biosource IDs
        """
        return self.get_field_values(self._biosource_id)

    def run(self, fail_on_error: bool = False):
        """
        run validation on each row

        wrapper of TableValidator.riun that also does sample validation
        """
        result = super().run(fail_on_error)

        if self.__require_unique_ids:
            result = self.validate_unqiue_identifiers(result, fail_on_error)

        return result
