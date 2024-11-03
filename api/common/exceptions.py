from math import ceil
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import Request, Response, status

RESPONSES = {404: {"description": "Not found"}}

def get_error_message(ex:Exception) -> None:
    """ returns last line of stack trace"""
    return '{0}: {1}'.format(ex.__class__.__name__, ex)


async def too_many_requests(request: Request, response: Response, pexpire: int):
    """
    default callback when too many requests
    :param request:
    :param pexpire: The remaining milliseconds
    :param response:
    :return:
    """
    expire = ceil(pexpire / 1000)

    raise StarletteHTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"Too Many Requests. Retry after {expire} seconds.",
        headers={"Retry-After": str(expire)},
    )