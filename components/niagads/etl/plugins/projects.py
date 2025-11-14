from enum import Enum


class RegisteredETLProject(Enum):
    """
    Enum for registered ETL projects and their plugin package paths.

    Each member maps a project name to its corresponding plugin package path.
    Used for dynamic plugin discovery and registration in the ETL pipeline.

    TODO: Add more mappings as needed.

    Attributes:
        GENOMICSDB: Plugin package path for the GenomicsDB project.

    """

    GENOMICSDB = "niagads.genomicsdb_service.etl.plugins"

    # after  https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str):  # allow to be case insensitive
        for member in cls:
            if member.name.lower() == value.lower():
                return member
        raise ValueError(f"{value!r} is not a valid {cls.__name__}")
