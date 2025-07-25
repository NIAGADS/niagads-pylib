"""Exception Handler Wrappers
Defintion and Usage after: https://github.com/fastapi/fastapi/issues/917#issuecomment-578381578
import in app main.py or Polylith base and call after app initialization:

For example:
```python
app = FastAPI()
add_runtime_exception_handler(app)
```

For niagads/bases that are open_access_api services, please copy the following
code into the `core.py` file after app initialization:

```python
add_runtime_exception_handler(app)
add_not_implemented_exception_handler(app)
add_validation_exception_handler(app)
add_system_exception_handler(app)
```

"""

import traceback
from math import ceil

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from niagads.exceptions.core import ValidationError
from niagads.api_common.config import Settings
from sqlalchemy.exc import DatabaseError
from starlette.exceptions import HTTPException as StarletteHTTPException


def add_runtime_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(RuntimeError)
    async def runtime_exception_handler(request: Request, exc: RuntimeError):
        query = request.url.path
        if request.url.query != "":
            query += "?" + request.url.query
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(
                {
                    "detail": str(exc),
                    "message": (
                        f"An unexpected error occurred.  Please submit a `bug` GitHub issue "
                        f"containing this full error response at: https://github.com/NIAGADS/niagads-api/issues"
                    ),
                    "stack_trace": [
                        t.replace("\n", "").replace('"', "'")
                        for t in traceback.format_tb(exc.__traceback__)
                    ],
                    "request": str(query),
                }
            ),
        )


def add_not_implemented_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(NotImplementedError)
    async def not_implemented_exception_handler(
        request: Request, exc: NotImplementedError
    ):
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=jsonable_encoder({"detail": str(exc)}),
        )


# XXX: request_validation & validation duplicated b/c couldn't
# assign two error types to one handler
# due to startlette runtime checks on the exception type
def add_request_validation_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: ValidationError
    ):

        raise HTTPException(
            status_code=422, detail=getattr(exc, "_errors") or f"{str(exc)}"
        )

        # TODO: match fastAPI or parse fastAPI validation error
        """
        {
        "detail": [
            {
            "type": "enum",
            "loc": [
                "query",
                "trait"
            ],
            "msg": "Input should be 'AD', 'ADRD', 'AD_ADRD' or 'ALL'",
            "input": "AD_ADRDX",
            "ctx": {
                "expected": "'AD', 'ADRD', 'AD_ADRD' or 'ALL'"
            }
            }
        ]
        }
        """


def add_validation_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        raise HTTPException(status_code=422, detail=f"{str(exc)}")


# XXX: OSError & DatabaseError handlers duplicated b/c couldn't
# assign two error types to one handler
# due to startlette runtime checks on the exception type
def add_system_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(OSError)
    async def system_exception_handler(request: Request, exc: OSError):
        query = request.url.path
        if request.url.query != "":
            query += "?" + request.url.query
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(
                {
                    "detail": str(exc),  # optionally, include the pydantic errors
                    "message": (
                        f"A system error occurred.  Please email this error response to "
                        f"{Settings.from_env().ADMIN_EMAIL} with the subject `NIAGADS API Systems Error`"
                        f"and we will try and resolve the issue as soon as possible."
                    ),
                    "stack_trace": [
                        t.replace("\n", "").replace('"', "'")
                        for t in traceback.format_tb(exc.__traceback__)
                    ],
                    "request": str(query),
                }
            ),
        )


def add_database_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(DatabaseError)
    async def database_exception_handler(request: Request, exc: DatabaseError):
        query = request.url.path
        if request.url.query != "":
            query += "?" + request.url.query
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(
                {
                    "detail": str(exc),  # optionally, include the pydantic errors
                    "message": (
                        f"A error occurred.  Please email this error response to "
                        f"{Settings.from_env().ADMIN_EMAIL} with the subject `NIAGADS API Systems Error`"
                        f"and we will try and resolve the issue as soon as possible."
                    ),
                    "stack_trace": [
                        t.replace("\n", "").replace('"', "'")
                        for t in traceback.format_tb(exc.__traceback__)
                    ],
                    "request": str(query),
                }
            ),
        )


# FIXME: does this belong here? re-evaluate when rate limits are imposed
async def too_many_requests(request: Request, response: Response, pexpire: int):
    """
    default callback when requests exceed rate limit

    Args:
        request (Request):
        response (Response):
        pexpire (int): remaining milliseconds

    Raises:
        StarletteHTTPException
    """

    expire = ceil(pexpire / 1000)

    raise StarletteHTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"Too Many Requests. Retry after {expire} seconds.",
        headers={"Retry-After": str(expire)},
    )
