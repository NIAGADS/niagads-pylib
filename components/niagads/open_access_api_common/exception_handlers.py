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
from typing import Union

from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from niagads.open_access_api_common.config.core import get_settings
from psycopg2 import DatabaseError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def add_runtime_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(RuntimeError)
    async def runtime_exception_handler(request: Request, exc: RuntimeError):
        query = request.url.path
        if request.url.query != "":
            query += "?" + request.url.query
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {
                    "error": str(exc),  # optionally, include the pydantic errors
                    "message": "An unexpected error occurred.  Please submit a `bug` GitHub issue containing this full error response at: https://github.com/NIAGADS/niagads-api/issues",
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {"error": str(exc), "message": "Not yet implemented"}
            ),
        )


def add_validation_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(Union[RequestValidationError, ValidationError])
    async def validation_exception_handler(
        request: Request, exc: Union[RequestValidationError, ValidationError]
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {"error": str(exc), "message": "Invalid parameter value"}
            ),
        )


def add_system_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(Union[OSError, DatabaseError])
    async def system_exception_handler(
        request: Request, exc: Union[OSError, DatabaseError]
    ):
        query = request.url.path
        if request.url.query != "":
            query += "?" + request.url.query
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {
                    "message": str(exc),  # optionally, include the pydantic errors
                    "error": (
                        f"An system error occurred.  Please email this error response to "
                        f"{get_settings().ADMIN_EMAIL} with the subject `NIAGADS API Systems Error`"
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
