from enum import Enum

ROUTE_TAGS = ['(Internal) Redirects']

class RedirectEndpoints(str, Enum):
    TABLE = '/view/table'