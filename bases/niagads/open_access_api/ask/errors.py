"""Adapt existing failures to safe ASK messages without copying error bodies."""

import re

import httpx
from aiohttp import ClientResponseError, ContentTypeError
from asgi_correlation_id import correlation_id
from niagads.api.common.services.embeddings import QueryEmbeddingError
from niagads.common.core import ComponentBaseMixin
from niagads.open_access_api.ask.contracts import AskErrorCode, AskIssue
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from starlette.exceptions import HTTPException

ACTIONS = {
    "search_genes": "Searching for genes",
    "search_tracks": "Searching for datasets",
    "gene": "Looking up the gene",
    "variant": "Looking up the variant",
    "track": "Looking up the dataset",
    "gene_structure": "Retrieving gene structure",
    "gene_associations": "Retrieving gene associations",
    "variant_associations": "Retrieving variant associations",
    "region_associations": "Retrieving region associations",
    "assistant": "Preparing the answer",
}

MESSAGES = {
    AskErrorCode.INVALID_INPUT: (
        "The input is invalid. Check the identifier or requested parameters."
    ),
    AskErrorCode.NOT_FOUND: "The requested record was not found. Check its identifier.",
    AskErrorCode.UNSUPPORTED: (
        "This operation is not available. Ask about another supported operation."
    ),
    AskErrorCode.AUTHENTICATION: "Sign in to access the requested information.",
    AskErrorCode.AUTHORIZATION: (
        "Your account does not have access to the requested information. Contact "
        "support if access is expected."
    ),
    AskErrorCode.RATE_LIMIT: (
        "The service is receiving too many requests. Wait before trying again."
    ),
    AskErrorCode.TIMEOUT: "The service did not respond in time. Try again later.",
    AskErrorCode.PROVIDER_ERROR: (
        "A required service is unavailable. Try again later; contact support if "
        "the problem continues."
    ),
    AskErrorCode.MALFORMED_RESPONSE: (
        "A required service returned an invalid response. Contact support if the "
        "problem continues."
    ),
    AskErrorCode.RESPONSE_TOO_LARGE: (
        "The returned data is too large to display. Request a smaller set of "
        "records."
    ),
    AskErrorCode.USAGE_LIMIT: (
        "This question needs more steps than ASK can complete. Split it into "
        "separate questions."
    ),
    AskErrorCode.INTERNAL_ERROR: (
        "An unexpected error prevented completion. Contact support with the "
        "request reference."
    ),
}


class RetrievalError(RuntimeError, ComponentBaseMixin):
    """Keep a safe failure alongside its original chained exception."""

    def __init__(self, issue: AskIssue, status_code: int | None = None):
        RuntimeError.__init__(self, issue.message)
        self.issue = issue
        self.status_code = status_code


def safe_request_id(value: str | None) -> str | None:
    """Accept only bounded request-reference tokens, never arbitrary header text.

    Args:
        value (str | None): An available request reference.

    Returns:
        str | None: A safe reference, or None.
    """
    return value if value and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value) else None


def issue_for_status(
    status: int, operation: str, request_id: str | None = None
) -> AskIssue:
    """Map HTTP status semantics without inspecting potentially sensitive bodies.

    Args:
        status (int): The failed HTTP response status.
        operation (str): A registered action name.
        request_id (str | None): Available API correlation reference.

    Returns:
        AskIssue: A safe action-specific failure.
    """
    code = {
        400: AskErrorCode.INVALID_INPUT,
        422: AskErrorCode.INVALID_INPUT,
        404: AskErrorCode.NOT_FOUND,
        401: AskErrorCode.AUTHENTICATION,
        403: AskErrorCode.AUTHORIZATION,
        429: AskErrorCode.RATE_LIMIT,
        408: AskErrorCode.TIMEOUT,
        504: AskErrorCode.TIMEOUT,
        405: AskErrorCode.UNSUPPORTED,
        501: AskErrorCode.UNSUPPORTED,
        502: AskErrorCode.PROVIDER_ERROR,
        503: AskErrorCode.PROVIDER_ERROR,
    }.get(status, AskErrorCode.INTERNAL_ERROR)
    return make_issue(code, operation, request_id)


def make_issue(
    code: AskErrorCode, operation: str, request_id: str | None = None
) -> AskIssue:
    """Build an action-specific message from controlled text.

    Args:
        code (AskErrorCode): The failure category.
        operation (str): A registered action name.
        request_id (str | None): Available API correlation reference.

    Returns:
        AskIssue: A safe failure for the model and browser.
    """
    return AskIssue(
        code=code,
        operation=operation,
        message=f"{ACTIONS[operation]} failed. {MESSAGES[code]}",
        request_id=safe_request_id(request_id or correlation_id.get()),
    )


def issue_for_provider_status(
    status: int,
    operation: str,
    request_id: str | None = None,
    provider_request_id: str | None = None,
) -> AskIssue:
    """Keep provider access failures distinct from the browser user's access.

    Args:
        status (int): The provider's HTTP status.
        operation (str): The failed registered action.
        request_id (str | None): API correlation reference.
        provider_request_id (str | None): Provider correlation reference.

    Returns:
        AskIssue: A safe failure with an appropriate action for the user.
    """
    issue = issue_for_status(status, operation, request_id)
    if status in {401, 403}:
        detail = (
            "A required service could not authenticate the request."
            if status == 401
            else "A required service denied access."
        )
        issue.message = (
            f"{ACTIONS[operation]} failed. {detail} "
            "Contact support with the request reference."
        )
    elif status == 501:
        issue.message = (
            f"{ACTIONS[operation]} failed. A required service does not support "
            "this action. Contact support."
        )
    elif status not in {429, 408, 504}:
        issue = make_issue(AskErrorCode.PROVIDER_ERROR, operation, request_id)
        if status < 500:
            issue.message = (
                f"{ACTIONS[operation]} failed. A required service rejected "
                "the request. Contact support with the request reference."
            )
    issue.provider_request_id = safe_request_id(provider_request_id)
    return issue


def issue_for_exception(
    exc: Exception, operation: str, request_id: str | None = None
) -> AskIssue:
    """Classify failures, separating provider access from user access.

    Args:
        exc (Exception): The original exception or its wrapper.
        operation (str): A registered action name.
        request_id (str | None): Available API correlation reference.

    Returns:
        AskIssue: A content-safe failure.
    """
    if isinstance(exc, RetrievalError):
        exc.issue.request_id = exc.issue.request_id or safe_request_id(
            request_id or correlation_id.get()
        )
        return exc.issue
    if isinstance(exc, QueryEmbeddingError):
        cause = exc.__cause__
        while isinstance(cause, QueryEmbeddingError):
            cause = cause.__cause__
        if isinstance(cause, ContentTypeError):
            issue = make_issue(AskErrorCode.MALFORMED_RESPONSE, operation, request_id)
        elif isinstance(cause, ClientResponseError):
            issue = issue_for_provider_status(
                cause.status,
                operation,
                request_id,
                (cause.headers or {}).get("x-request-id"),
            )
        elif isinstance(cause, TimeoutError):
            issue = make_issue(AskErrorCode.TIMEOUT, operation, request_id)
        else:
            code = (
                AskErrorCode.MALFORMED_RESPONSE
                if isinstance(cause, (ValueError, KeyError, TypeError))
                else AskErrorCode.PROVIDER_ERROR
            )
            issue = make_issue(code, operation, request_id)
        issue.provider_request_id = issue.provider_request_id or safe_request_id(
            exc.request_id
        )
        return issue
    if isinstance(exc, ModelHTTPError):
        return issue_for_provider_status(
            exc.status_code,
            operation,
            request_id,
            (exc.headers or {}).get("x-request-id"),
        )
    if isinstance(exc, (httpx.HTTPStatusError, HTTPException)):
        status = (
            exc.response.status_code
            if isinstance(exc, httpx.HTTPStatusError)
            else exc.status_code
        )
        return issue_for_status(status, operation, request_id)
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        code = AskErrorCode.TIMEOUT
    elif isinstance(exc, UsageLimitExceeded):
        code = AskErrorCode.USAGE_LIMIT
    elif isinstance(exc, UnexpectedModelBehavior):
        code = AskErrorCode.MALFORMED_RESPONSE
    elif isinstance(exc, ModelAPIError):
        cause = exc.__cause__ or exc.__context__
        code = (
            AskErrorCode.TIMEOUT
            if isinstance(cause, (TimeoutError, httpx.TimeoutException))
            else AskErrorCode.PROVIDER_ERROR
        )
    elif isinstance(exc, httpx.RequestError):
        code = AskErrorCode.PROVIDER_ERROR
    else:
        code = AskErrorCode.INTERNAL_ERROR
    return make_issue(code, operation, request_id)
