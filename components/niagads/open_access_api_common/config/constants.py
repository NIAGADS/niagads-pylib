# http client
HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 10

# Responses
RESPONSES = {
        404: {"description": "Item not found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
        501: {"description": "Not Implemented"},
        429: { "description": "Too many requests"}
    }

# regular expressions
SHARD_PATTERN = r"chr(\d{1,2}|[XYM]|MT)"

# default values
DEFAULT_NULL_STRING = "NA"
