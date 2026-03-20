from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class ETLExecutionMode(CaseInsensitiveEnum):
    """
    ETL execution mode:
    - DRY_RUN: Simulate ETL, do not write or commit any changes to the database.
    - RUN: run the full ETL Plugin
    - UNDO: undo a previous the plugin
    - PREPROCESS: generate intermediary load files
    """

    DRY_RUN = auto()
    PREPROCESS = auto()
    RUN = auto()
    UNDO = auto()
