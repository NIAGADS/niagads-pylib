from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class ETLMode(CaseInsensitiveEnum):
    """
    ETL execution mode:
    - COMMIT: Perform ETL and commit all changes to the database.
    - NON_COMMIT: Perform ETL but roll back all changes at the end (no commit).
    - DRY_RUN: Simulate ETL, do not write or commit any changes to the database.
    - PREPROCESS: generate intermediary load files
    """

    COMMIT = auto()
    NON_COMMIT = auto()
    DRY_RUN = auto()
    PREPROCESS = auto()
