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
        self, base_url: str, timeout: int = _HTTP_CLIENT_TIMEOUT, debug: bool = False
    ):
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self.__base_url = base_url
        self.__session_timeout: int = timeout
        self.__connector: TCPConnector = None
        self.__session: ClientSession = None

    # this will allow us to construct statements like:
    # async with HttpClientSessionManager to automatically
    # handle open and closing the session and connection
    # outside of API applications where it needs to be
    # persistant
    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def create(self):
        self.__connector = TCPConnector(limit=50)
        self.__session = ClientSession(
            base_url=self.__base_url,
            connector=self.__connector,
            timeout=ClientTimeout(total=self.__session_timeout),
            raise_for_status=True,
            trace_configs=self.__initialize_trace_config(),
        )

    async def ensure_session(self):
        if self.__session is None or self.__session.closed:
            await self.create()

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

    async def handle_request(self, params: HttpRequest, toJson=False):
        await self.ensure_session()
        try:
            async with self.__session.request(
                params.method, params.endpoint, params=params.params
            ) as response:
                if toJson:
                    return await response.json()
                else:
                    return await response.text()
        except Exception as e:
            self.logger.exception(f"Request failed: {e}")
            raise

    async def fetch_json(self, endpoint: str, params: dict):
        """wrapper for send_request that does a fetch (get) and retrieves JSON response
        errors are handled in send_request"""
        request_params = HttpRequest(params=params, endpoint=endpoint)
        response = await self.handle_request(request_params, toJson=True)
        return response

    async def fetch_text(self, endpoint: str, params: dict) -> str:
        """Wrapper for send_request that fetches raw text response (for XML, etc)."""
        request_params = HttpRequest(params=params, endpoint=endpoint)
        response = await self.handle_request(request_params)
        return response

    async def close(self):
        if self.__session is not None:
            await self.__session.close()
        if self.__connector is not None:
            await self.__connector.close()

    async def __call__(self) -> ClientSession:
        await self.ensure_session()
        return self.__session
