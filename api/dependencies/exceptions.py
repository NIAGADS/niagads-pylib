from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

RESPONSES = {404: {"description": "Not found"}}

def get_error_message(ex:Exception) -> None:
    """ returns last line of stack trace"""
    return '{0}: {1}'.format(ex.__class__.__name__, ex)