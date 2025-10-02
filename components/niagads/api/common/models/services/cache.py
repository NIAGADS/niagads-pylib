from enum import StrEnum, auto

from fastapi import Request
from niagads.api.common.models.response.request import RequestDataModel
from niagads.utils.string import blake2b_hash, matches, regex_replace
from pydantic import BaseModel, Field


class CacheNamespace(StrEnum):
    """Cache namespaces."""

    FILER = auto()  # FILER endpoints
    EXTERNAL_API = auto()  # external FILER API endpoints
    GENOMICS = auto()  # genomics endpoints
    ADVP = auto()  # advp endpoints
    VIEW = auto()  # view redirect endpoints
    ROOT = auto()  # root api
    QUERY_CACHE = auto()  # for server-side pagination, sorting, filtering


class CacheKeyQualifier(StrEnum):
    """Qualifiers for cache keys."""

    PAGE = "pagination-page"
    CURSOR = "pagination-cursor"
    RESULT_SIZE = "pagination-result-size"
    RAW = auto()
    QUERY_CACHE = auto()
    REQUEST_PARAMETERS = "request"
    VIEW = "view_"

    def __str__(self):
        return f"_{self.value}"


class CacheKeyDataModel(BaseModel, arbitrary_types_allowed=True):
    """Generates and stores cache key for the response, given the originating request.

    includes member and static functions for
    encyption of keys and removing view related query props
    """

    key: str  # in memory cached key
    namespace: CacheNamespace = Field(description="namespace in the in-memory cache")

    @classmethod
    async def from_request(cls, request: Request):
        endpoint = str(request.url.path)  # endpoint includes path parameters
        parameters = RequestDataModel.sort_query_parameters(
            dict(request.query_params), exclude=["format", "view"]
        )
        rawKey = (
            endpoint + "?" + parameters.replace(":", "_")
        )  # ':' delimitates keys in keydb

        namespace = cls.__get_namespace_from_path(request.url.path)
        return cls(key=rawKey, namespace=namespace)

    @staticmethod
    def __get_namespace_from_path(path: str):
        # endpoints are /, /version/namespace/route /version /version/route
        elements = path.split("/")
        for el in elements:
            try:
                return CacheNamespace(el)
            except ValueError:
                continue

        return CacheNamespace("root")

    def encrypt(self):
        return self.encrypt_key(self.key)

    def no_page(self):
        return self.remove_query_props(self.key, "page")

    @staticmethod
    def remove_query_props(key: str, prop: str):
        pattern = r"\b" + prop + r"=[^&]*&?\s*"
        newKey = regex_replace(pattern, "", key)
        return regex_replace("&$", "", newKey)  # remove terminal '&' if present

    @staticmethod
    def encrypt_key(key: str = None):
        return blake2b_hash(key)
