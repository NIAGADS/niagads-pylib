HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 100

# Responses

RESPONSES = {
    404: {"description": "Record not found"},
    422: {"description": "Parameter Validation Error"},
    429: {"description": "Too many requests"},
}


# regular expressions
SHARD_PATTERN = r"chr(\d{1,2}|[XYM]|MT)"

# default values
DEFAULT_NULL_STRING = "NA"
