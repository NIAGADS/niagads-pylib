from datetime import datetime
from enum import auto
from typing import Optional

from niagads.common.models.core import TransformableModel
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
    OTHER = auto()


class CurationActorType(CaseInsensitiveEnum):
    """Actor types for curation events."""

    USER = auto()
    SERVICE = auto()
    PIPELINE = auto()


class CurationEvent(TransformableModel):
    """Record of a single curation/processing action applied to a Track.

    Minimal, user-facing fields only. Designed to be serialised as part of
    `Track.curation_history` and to be easily mappable to provenance/activity
    records if required later.
    """

    event_date: datetime = Field(title="Event date")
    event_type: CurationEventType = Field(
        default=CurationEventType.STANDARDIZE, title="Event type"
    )
    actor: Optional[str] = Field(
        default="NIAGADS", title="Agent performing the event (user or service)"
    )
    actor_type: Optional[CurationActorType] = Field(
        default=None, description="user|service|pipeline"
    )
    tool: Optional[str] = Field(default=None, title="Software or pipeline name")
    tool_version: Optional[str] = Field(default=None)
