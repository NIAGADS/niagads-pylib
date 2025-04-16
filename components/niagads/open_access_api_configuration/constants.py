# application db
CONNECTION_POOL_SIZE = 10

# cache db
# int or float in seconds specifying maximum timeout for the operations to last. By default (aiocache) its 5. Use 0 or None if you want to disable it.
CACHEDB_TIMEOUT = 5

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
