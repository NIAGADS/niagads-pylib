"""Signed response references and end-user feedback for Logfire."""

import hmac
from typing import Literal

import logfire
from niagads.common.models.base import CustomBaseModel
from opentelemetry._logs import SeverityNumber, get_logger
from pydantic import ConfigDict, Field, SecretStr


class AskFeedback(CustomBaseModel):
    """A rating and optional comment for a server-issued response reference."""

    model_config = ConfigDict(extra="forbid", strict=True)

    reference: str = Field(pattern=r"^00-[0-9a-f]{32}-[0-9a-f]{16}-01\.[0-9a-f]{64}$")
    rating: Literal[0, 1]
    comment: str | None = Field(default=None, max_length=2000)


def create_feedback_reference(secret: SecretStr) -> str | None:
    """Sign the active response context when its trace is sampled.

    Args:
        secret (SecretStr): Shared API-worker signing secret.

    Returns:
        str | None: Signed trace reference, or None without a sampled trace.
    """
    traceparent = logfire.get_context().get("traceparent")
    if not traceparent or not traceparent.endswith("-01"):
        return None
    signature = hmac.digest(
        secret.get_secret_value().encode(), traceparent.encode(), "sha256"
    ).hex()
    return f"{traceparent}.{signature}"


def record_feedback(feedback: AskFeedback, secret: SecretStr) -> None:
    """Verify the response reference and emit feedback in its original context.

    Args:
        feedback (AskFeedback): Validated rating and optional comment.
        secret (SecretStr): Shared API-worker signing secret.

    Raises:
        ValueError: If the reference signature is invalid.
    """
    traceparent, signature = feedback.reference.rsplit(".", 1)
    expected = hmac.digest(
        secret.get_secret_value().encode(), traceparent.encode(), "sha256"
    ).hex()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid feedback reference")
    attributes = {
        "gen_ai.evaluation.target": "ask-niagads",
        "gen_ai.evaluation.name": "user_helpfulness",
        "gen_ai.evaluation.score.value": float(feedback.rating),
        "gen_ai.agent.name": "ask-niagads",
    }
    if feedback.comment:
        attributes["gen_ai.evaluation.explanation"] = feedback.comment
    with logfire.attach_context({"traceparent": traceparent}):
        get_logger("niagads.ask.feedback").emit(
            event_name="gen_ai.evaluation.result",
            severity_number=SeverityNumber.INFO,
            body="ASK NIAGADS user feedback",
            attributes=attributes,
        )
