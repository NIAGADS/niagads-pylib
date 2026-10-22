"""Exception handlers used by NIAGADS FastAPI applications."""

import json
import traceback
from math import ceil

from fastapi import FastAPI, Request, Response, status
from fastapi.exception_handlers import (
    request_validation_exception_handler as fastapi_request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from niagads.api.common.config import Settings
from sqlalchemy.exc import DatabaseError
from starlette.exceptions import HTTPException as StarletteHTTPException


def _request_url(request: Request) -> str:
    """Build the request path, including its query string.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        str: The request path and query string.
    """

    query = request.url.path
    if request.url.query:
        query += "?" + request.url.query
    return query


def _service_error_response(
    request: Request,
    exc: OSError | DatabaseError,
    message: str,
) -> JSONResponse:
    """Build a response for a system or database service failure.

    Args:
        request (Request): The incoming HTTP request.
        exc (OSError | DatabaseError): The exception being handled.
        message (str): The user-facing error message.

    Returns:
        JSONResponse: The service-unavailable response.
    """

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": str(exc),
            "message": message,
            "stack_trace": [
                trace.replace("\n", "").replace('"', "'")
                for trace in traceback.format_tb(exc.__traceback__)
            ],
            "request": _request_url(request),
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


async def runtime_exception_handler(
    request: Request,
    exc: RuntimeError,
) -> JSONResponse:
    """Handle runtime errors, preserving wrapped request validation errors.

    Args:
        request (Request): The incoming HTTP request.
        exc (RuntimeError): The runtime exception being handled.

    Returns:
        JSONResponse: The validation-error or internal-server-error response.
    """

    original = exc
    while original is not None:
        if isinstance(original, RequestValidationError):
            return await request_validation_exception_handler(request, original)
        original = original.__cause__ or original.__context__

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": (
                "An unexpected error occurred. Please submit a `bug` GitHub issue "
                "containing this full error response and request ID at: "
                "https://github.com/NIAGADS/niagads-api/issues"
            ),
            "stack_trace": [
                trace.replace("\n", "").replace('"', "'")
                for trace in traceback.format_tb(exc.__traceback__)
            ],
            "request": _request_url(request),
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


async def not_implemented_exception_handler(
    request: Request,
    exc: NotImplementedError,
) -> JSONResponse:
    """Handle an unimplemented operation.

    Args:
        request (Request): The incoming HTTP request.
        exc (NotImplementedError): The exception being handled.

    Returns:
        JSONResponse: The not-implemented response.
    """

    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": str(exc)},
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> Response:
    """Preserve validation details with the request reference and traceback.

    Args:
        request (Request): The incoming HTTP request.
        exc (RequestValidationError): The request validation exception.

    Returns:
        Response: The validation-error response with diagnostic details.
    """

    response = await fastapi_request_validation_exception_handler(request, exc)
    content = json.loads(response.body)
    content.update(
        stack_trace=traceback.format_exception(exc),
        request=_request_url(request),
        request_id=request.headers.get("X-Request-ID"),
    )
    return JSONResponse(status_code=response.status_code, content=content)


async def system_exception_handler(
    request: Request,
    exc: OSError,
) -> JSONResponse:
    """Handle an operating-system service failure.

    Args:
        request (Request): The incoming HTTP request.
        exc (OSError): The operating-system exception being handled.

    Returns:
        JSONResponse: The service-unavailable response.
    """

    return _service_error_response(
        request,
        exc,
        (
            "A system error occurred. Please email this error response to "
            f"{Settings.from_env().ADMIN_EMAIL} with the subject `NIAGADS API "
            "Systems Error`, including the request ID, and we will try and "
            "resolve the issue as soon as possible."
        ),
    )


async def database_exception_handler(
    request: Request,
    exc: DatabaseError,
) -> JSONResponse:
    """Handle a database service failure.

    Args:
        request (Request): The incoming HTTP request.
        exc (DatabaseError): The database exception being handled.

    Returns:
        JSONResponse: The service-unavailable response.
    """

    return _service_error_response(
        request,
        exc,
        (
            "A database error occurred. Please email this error response to "
            f"{Settings.from_env().ADMIN_EMAIL} with the subject `NIAGADS API "
            "Systems Error`, including the request ID, and we will try and "
            "resolve the issue as soon as possible."
        ),
    )


def add_runtime_exception_handler(app: FastAPI) -> None:
    """Register the runtime-error handler with a FastAPI application.

    Args:
        app (FastAPI): The application receiving the exception handler.
    """

    app.add_exception_handler(RuntimeError, runtime_exception_handler)


def add_not_implemented_exception_handler(app: FastAPI) -> None:
    """Register the not-implemented handler with a FastAPI application.

    Args:
        app (FastAPI): The application receiving the exception handler.
    """

    app.add_exception_handler(NotImplementedError, not_implemented_exception_handler)


def add_request_validation_exception_handler(app: FastAPI) -> None:
    """Register the request-validation handler with a FastAPI application.

    Args:
        app (FastAPI): The application receiving the exception handler.
    """

    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )


def add_system_exception_handler(app: FastAPI) -> None:
    """Register the operating-system error handler with a FastAPI application.

    Args:
        app (FastAPI): The application receiving the exception handler.
    """

    app.add_exception_handler(OSError, system_exception_handler)


def add_database_exception_handler(app: FastAPI) -> None:
    """Register the database error handler with a FastAPI application.

    Args:
        app (FastAPI): The application receiving the exception handler.
    """

    app.add_exception_handler(DatabaseError, database_exception_handler)


# FIXME: does this belong here? Re-evaluate when rate limits are imposed.
async def too_many_requests(request: Request, response: Response, pexpire: int):
    """Raise the default exception used when requests exceed the rate limit.

    Args:
        request: The incoming request.
        response: The outgoing response.
        pexpire: Remaining expiration time in milliseconds.

    Raises:
        StarletteHTTPException: Always raised with a 429 status.
    """

    expire = ceil(pexpire / 1000)

    raise StarletteHTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"Too Many Requests. Retry after {expire} seconds.",
        headers={"Retry-After": str(expire)},
    )
