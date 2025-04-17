"""Manager for a KeyDB key-value cache store"""

from niagads.open_access_api_configuration.constants import CACHEDB_TIMEOUT
from niagads.open_access_api_configuration.core import get_settings
from typing_extensions import Self
from aiocache import RedisCache

from enum import Enum, StrEnum, auto
from aiocache.serializers import StringSerializer, JsonSerializer, PickleSerializer


class CacheSerializer(Enum):
    """Type of serializer to use when caching."""

    STRING = StringSerializer
    JSON = JsonSerializer
    PICKLE = PickleSerializer


class CacheTTL(Enum):
    """Time to Live (TTL) options for caching; in seconds."""

    DEFAULT = 3600  # 1 hr
    SHORT = 300  # 5 minutes
    DAY = 86400


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


class CacheManager:
    """KeyDB (Redis) cache for responses
    application will instantiate two CacheManagers
        1.  internal cache - for internal use in the FAST-API application
            * pickled responses
            * auto generated key based on request & params
        2. external cache -- for use by external (e.g., next.js) applications
            * json serialization of transformed responses
            * keyed on `requestId_view` or `_view_element`
    """

    __cache: RedisCache = None
    __namespace: CacheNamespace = CacheNamespace.ROOT
    __ttl: CacheTTL = CacheTTL.DEFAULT

    def __init__(
        self,
        serializer: CacheSerializer = CacheSerializer.JSON,
        namespace: CacheNamespace = None,
        ttl=CacheTTL.DEFAULT,
    ):
        connectionString = get_settings().CACHE_DB_URI
        config = self.__parse_uri_path(connectionString)

        # instantiate the serializer
        self.__cache = RedisCache(serializer=serializer.value(), **config)

        if namespace is not None:
            self.__namespace = namespace

        self.__ttl = CacheTTL[ttl]

    def set_TTL(self, ttl: CacheTTL):
        """Set time to life.

        Options: DEFAULT -> hour, SHORT -> 5 mins, DAY -> 24 hrs
        """
        self.__ttl = ttl

    def __parse_uri_path(self, uri: str):
        """Preparsing of the database URI.

        RedisCache.parse_uri_path() does not work as expected for the keydb URI""
        """
        values = uri.split("/")
        host, port = values[2].split(":")
        config = {
            "namespace": self.__namespace.value,
            "db": int(values[-1]),
            "port": int(port),
            "endpoint": host,
        }  # conceptually, endpoint here is the host IP
        return config

    async def set(
        self,
        cacheKey: str,
        value: any,
        ttl: CacheTTL = None,
        namespace: CacheNamespace = None,
        timeout: float = CACHEDB_TIMEOUT,
    ) -> None:
        """
        Set a key-value pair in the cache database.

        Args:
            cacheKey (str): _description_
            value (any): object to be cached
            ttl (CacheTTL, optional): cache pair TTL; for overriding the manager TTL setting. Defaults to None.
            namespace (CacheNamespace, optional): cache pair namespace; for overriding the manager namespace setting. Defaults to None.
            timeout (float, optional): timeout for the caching operation; for overriding the manager timeout. Defaults to CACHEDB_TIMEOUT.

        Raises:
            RuntimeError: raised if the connection is not initialized
        """
        if ttl is None:
            ttl = self.__ttl
        if self.__cache is None:
            raise RuntimeError("In memory cache not initialized")
        ns = self.__namespace if namespace is None else namespace
        await self.__cache.set(
            cacheKey, value, ttl=ttl.value, namespace=ns.value, timeout=timeout
        )

    async def get(
        self,
        cacheKey: str,
        namespace: CacheNamespace = None,
        timeout: float = CACHEDB_TIMEOUT,
    ) -> any:
        """
        Get value assigned to a key and (optional) namespace.

        Args:
            cacheKey (str): the cache key
            namespace (CacheNamespace, optional): the namespace. Defaults to None.
            timeout (float, optional): timeout for the caching operation; for overriding the manager timeout. Defaults to CACHEDB_TIMEOUT.

        Raises:
            RuntimeError: raised if the connection is not initialized

        Returns:
            any: the object identified by the cache key
        """
        if self.__cache is None:
            raise RuntimeError("In memory cache not initialized")
        ns = self.__namespace if namespace is None else namespace
        return await self.__cache.get(cacheKey, namespace=ns.value, timeout=timeout)

    async def exists(
        self,
        cacheKey: str,
        namespace: CacheNamespace = None,
        timeout: float = CACHEDB_TIMEOUT,
    ) -> bool:
        """
        Check to see if a cache key exists in a namespace (optional).

        Args:
            cacheKey (str): the cache key
            namespace (CacheNamespace, optional): the namespace. Defaults to None.
            timeout (float, optional): timeout for the caching operation; for overriding the manager timeout. Defaults to CACHEDB_TIMEOUT.

        Raises:
            RuntimeError: raised if the connection is not initialized

        Returns:
            bool: True if the key exists; False otherwise.
        """
        if self.__cache is None:
            raise RuntimeError("In memory cache not initialized")
        ns: CacheNamespace = self.__namespace if namespace is None else namespace
        return await self.__cache.exists(cacheKey, namespace=ns.value, timeout=timeout)

    async def get_cache(self) -> RedisCache:
        return self.__cache

    async def __call__(self) -> Self:
        return self
