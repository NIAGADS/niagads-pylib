from starlette.exceptions import HTTPException as StarletteHTTPException

RESPONSES = {404: {"description": "Not found"}}

def get_error_message(ex:Exception) -> None:
    """ returns last line of stack trace"""
    return '{0}: {1}'.format(ex.__class__.__name__, ex)