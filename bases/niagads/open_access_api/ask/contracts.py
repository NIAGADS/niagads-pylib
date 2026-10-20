"""Validated result and presentation contracts; datasets never come from the LLM."""

from typing import Any, Literal
from uuid import uuid4

from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.common.models.base import CustomBaseModel
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import ConfigDict, Field


class AskErrorCode(CaseInsensitiveEnum):
    """Safe failure categories shared by ASK tools and browser results."""

    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    MALFORMED_RESPONSE = "malformed_response"
    RESPONSE_TOO_LARGE = "response_too_large"
    USAGE_LIMIT = "usage_limit"
    INTERNAL_ERROR = "internal_error"


class AskIssue(CustomBaseModel):
    """A safe operation failure; raw exceptions remain on the server."""

    model_config = ConfigDict(extra="forbid")

    code: AskErrorCode
    operation: str
    message: str
    request_id: str | None = None
    provider_request_id: str | None = None


class Evidence(CustomBaseModel):
    """One independently attributable item of gene-association evidence."""

    model_config = ConfigDict(extra="forbid")

    evidence_type: Literal["curated", "proximity"]
    data_source: str = Field(min_length=1)
    phenotype: str | None = None
    variant: str | None = None
    window: str | None = None
    assertion: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class ResultSet(CustomBaseModel):
    """A bounded page of authoritative API data with explicit provenance."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: Literal[
        "genes", "variants", "tracks", "associations", "structure", "operations"
    ]
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    page: int = Field(default=1, ge=1, le=MAX_NUM_PAGES)
    limit: int = Field(default=50, ge=1, le=100)
    has_more: bool = False
    sources: list[str] = Field(default_factory=list, max_length=100)
    parameters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class Presentation(CustomBaseModel):
    """A registry selection, never executable frontend code or arbitrary options."""

    model_config = ConfigDict(extra="forbid")

    component: Literal["table", "association_source_bar"]
    result_id: str = Field(min_length=1)
    title: str = Field(default="Retrieved evidence", max_length=160)
    slot: Literal["primary", "secondary"] = "primary"


class AskResponse(CustomBaseModel):
    """A complete structured part of a conversation response."""

    model_config = ConfigDict(extra="forbid")

    issues: list[AskIssue] = Field(default_factory=list)
    version: Literal[1] = 1
    status: Literal[
        "ok",
        "empty",
        "clarification",
        "unsupported",
        "retrieval_error",
        "provider_error",
        "invalid_presentation",
    ] = "ok"
    results: list[ResultSet] = Field(default_factory=list, max_length=12)
    presentation: list[Presentation] = Field(default_factory=list, max_length=6)
    warnings: list[str] = Field(default_factory=list)
