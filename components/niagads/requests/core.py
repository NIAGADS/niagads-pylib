from enum import auto
import logging

from aiohttp import (
    ClientSession,
    ClientTimeout,
    TraceConfig,
    TraceRequestStartParams,
    TraceRequestEndParams,
    TraceRequestExceptionParams,
)
from aiohttp.connector import TCPConnector
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel

_HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds


class HttpRequestMethod(CaseInsensitiveEnum):
    GET = auto()
    # PUT = quto()
    # POST = auto()


class HttpRequest(BaseModel):
    params: dict
    endpoint: str
    method: HttpRequestMethod = HttpRequestMethod.GET


class HttpClientSessionManager:
    """Create Http connection pool and request a session"""

    def __init__(
        self, baseUrl: str, timeout: int = _HTTP_CLIENT_TIMEOUT, debug: bool = False
    ):
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self.__baseUrl = baseUrl
        self.__connector: TCPConnector = TCPConnector(limit=50)
        self.__session: ClientSession = ClientSession(
            self.__baseUrl,
            connector=self.__connector,
            timeout=ClientTimeout(total=timeout),
            raise_for_status=True,
            trace_configs=self.__initialize_trace_config(),
        )

    async def __on_request_start(
        self, session, context, params: TraceRequestStartParams
    ):
        self.logger.debug(f"Request started: {params.method} {params.url}")

    async def __on_request_end(self, session, context, params: TraceRequestEndParams):
        self.logger.debug(
            f"Request ended: {params.method} {params.url} Status: {params.response.status}"
        )

    async def __on_request_exception(
        self, session, context, params: TraceRequestExceptionParams
    ):
        self.logger.error(
            f"Request exception: {params.method} {params.url} Error: {params.exception}"
        )

    def __initialize_trace_config(self):
        config = TraceConfig()
        if self._debug:
            config.on_request_start.append(self.__on_request_start)
            config.on_request_end.append(self.__on_request_end)
            config.on_request_exception.append(self.__on_request_exception)
        return [config]

    async def send_request(self, params: HttpRequest, returnJson: bool = False):
        try:
            async with self.__session.request(
                params.method, params.endpoint, params=params.params
            ) as response:
                if returnJson:
                    result = await response.json()
                else:
                    result = await response
                return result
        except Exception as e:
            self.logger.exception(f"Request failed: {e}")
            raise

    async def fetch_json(self, endpoint: str, params: dict):
        """wrapper for send_request that does a fetch (get) and retrieves JSON response
        errors are handled in send_request"""
        requestParams = HttpRequest(params=params, endpoint=endpoint)
        result = await self.send_request(requestParams, returnJson=True)
        return result

    async def close(self):
        if self.__session is not None:
            await self.__session.close()
        if self.__connector is not None:
            await self.__connector.close()

    async def __call__(self) -> ClientSession:
        if self.__session is None:
            raise Exception(
                f"HTTP client session manager for {self.__baseUrl} not initialized"
            )
        return self.__session
