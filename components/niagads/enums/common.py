from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class ProcessStatus(CaseInsensitiveEnum):
    SUCCESS = auto()
    FAIL = auto()
    RUNNING = auto()
