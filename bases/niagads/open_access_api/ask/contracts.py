"""Validated result and presentation contracts; datasets never come from the LLM."""

from typing import Any, Literal
from uuid import uuid4

from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.api.common.types import AnnotationKind, ResponseContent
from niagads.common.models.base import CustomBaseModel
from niagads.common.types import Entity
from pydantic import ConfigDict, Field


class AskIssue(CustomBaseModel):
    """An unavailable capability reported without failing the conversation."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["unsupported"]
    operation: str
    message: str
    request_id: str | None = None
    provider_request_id: str | None = None


class ResultSet(CustomBaseModel):
    """A bounded page of authoritative API data with explicit provenance."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    entity: Entity
    annotation: AnnotationKind | None = Field(
        description="Annotation kind, or null for search candidates."
    )
    content: ResponseContent = ResponseContent.FULL
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    page: int = Field(default=1, ge=1, le=MAX_NUM_PAGES)
    limit: int = Field(default=50, ge=1, le=100)
    has_more: bool = False
    sources: list[str] = Field(default_factory=list, max_length=100)
    parameters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PresentationIntent(CustomBaseModel):
    """User-facing view preference; frontend adapters own how it is fulfilled."""

    model_config = ConfigDict(extra="forbid")

    result_id: str = Field(min_length=1)
    view: Literal["auto", "table", "plot"] = "auto"
    title: str = Field(default="Retrieved evidence", max_length=160)
    plot_type: str | None = Field(default=None, min_length=1)
    group_by: str | None = Field(default=None, min_length=1)
    x: str | None = Field(default=None, min_length=1)
    y: str | None = Field(default=None, min_length=1)


class AskResponse(CustomBaseModel):
    """A complete structured part of a conversation response."""

    model_config = ConfigDict(extra="forbid")

    issues: list[AskIssue] = Field(default_factory=list)
    version: Literal[4] = 4
    status: Literal[
        "ok",
        "empty",
        "clarification",
        "unsupported",
        "retrieval_error",
        "provider_error",
    ] = "ok"
    results: list[ResultSet] = Field(default_factory=list, max_length=12)
    presentation: list[PresentationIntent] = Field(default_factory=list, max_length=6)
    warnings: list[str] = Field(default_factory=list)
