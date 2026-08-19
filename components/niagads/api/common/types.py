"""Common API type definitions.

This module defines small shared types used across the NIAGADS API,
"""

from enum import auto

from niagads.enums.core import CaseInsensitiveEnum


class ResponseView(CaseInsensitiveEnum):
    """enum for allowable response views"""

    FULL = auto()
    SUMMARY = auto()
    URLS = auto()
    COUNTS = auto()
    IDS = auto()


class ResponseFormat(CaseInsensitiveEnum):
    """enum for allowable response / output formats"""

    JSON = auto()
    TEXT = auto()


class ResponseLayout(CaseInsensitiveEnum):
    TABLE = auto()
    IGV_CONFIG = auto()
    IGV_TRACK_SELECTOR = auto()
    CHART = auto()
    DEFAULT = auto()


class Entity(CaseInsensitiveEnum):
    """Enumeration of entity types used in the API.
    Members:
        GENE: Represents a gene entity.
        VARIANT: Represents a variant entity.
        REGION: Represents a span entity.
        TRACK: Represents a track entity.
        COLLECTION: Represents a collection entity.
    """

    GENE = "gene"
    VARIANT = "variant"
    REGION = "region"
    TRACK = "track"
    COLLECTION = "collection"

    def __str__(self):
        """Return a human-friendly title-cased name for the entity.

        Returns:
            str: Title-cased string of the enum value (e.g., "Gene", "Variant").
        """

        return self.value.title()
