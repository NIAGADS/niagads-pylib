"""`Track` (metadata) database model"""

from enum import auto

from niagads.enums.core import CaseInsensitiveEnum


class TrackDataStore(CaseInsensitiveEnum):
    GENOMICS = auto()
    FILER = auto()
    SHARED = auto()
