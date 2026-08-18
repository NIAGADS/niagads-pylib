"""Common API type definitions.

This module defines small shared types used across the NIAGADS API,
"""

from niagads.enums.core import CaseInsensitiveEnum


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
