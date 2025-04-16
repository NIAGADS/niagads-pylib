from enum import auto, StrEnum


class DataStore(StrEnum):
    GENOMICS = auto()
    FILER = auto()
    SHARED = auto()
