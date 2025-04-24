# http client
HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 10

# Responses
# FIXME: not sure if this is needed and/or goes in exceptions
RESPONSES = {404: {"description": "Not found"}}

# regular expressions
SHARD_PATTERN = r"chr(\d{1,2}|[XYM]|MT)"

# default values
DEFAULT_NULL_STRING = "NA"
