from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class ETLOperation(CaseInsensitiveEnum):
    """
    Type of ETL operation:
    - LOAD: Insert new or Update existing records.
    - UPDATE: Update existing records.
    - DELETE: Delete records.
    - PATCH: Partially update records.
    - INSERT: Insert new records.
    """

    INSERT = auto()
    UPDATE = auto()
    LOAD = auto()
    PATCH = auto()
    DELETE = auto()
    SKIP = auto()
