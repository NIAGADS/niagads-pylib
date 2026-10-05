from enum import auto
from typing import Optional

from niagads.common.models.base import CustomBaseModel
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import Field


class CurationEventType(CaseInsensitiveEnum):
    """Controlled vocabulary for curation event types."""

    PREPROCESS = auto()
    VALIDATE = auto()
    STANDARDIZE = auto()
    HARMONIZE = auto()
    ENRICH = auto()
    REEMBED = auto()
    FILTER = auto()
    OTHER = auto()


class CurationActorType(CaseInsensitiveEnum):
    """Actor types for curation events."""

    PERSON = auto()  # idividual curator
    ORGANIZATION = auto()  # institution or team
    SOFTWARE = auto()  # automated tool or pipeline


class CurationEvent(CustomBaseModel):
    """Record of a single curation/processing action applied to a Track.

    Minimal, user-facing fields only. Designed to be serialised as part of
    `Track.curation_history` and to be easily mappable to provenance/activity
    records if required later.
    """

    event_date: str = Field(title="Event date")
    event_type: CurationEventType = Field(
        default=CurationEventType.STANDARDIZE, title="Event Type"
    )
    actor: Optional[str] = Field(
        default="NIAGADS", description="Agent performing the event (user or service)"
    )
    actor_type: Optional[CurationActorType] = Field(
        default=CurationActorType.ORGANIZATION,
        title="Actor Type",
        description=f"One of {CurationActorType.list()}",
    )
    tool: Optional[str] = Field(default=None, description="Software or pipeline name")
    tool_version: Optional[str] = Field(default=None)
    description: str = Field(
        ...,
    )
