from aiohttp import ClientSession, ClientTimeout
from aiohttp.connector import TCPConnector

_HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds


class HttpClientSessionManager:
    """Create Http connection pool and request a session"""

    def __init__(self, baseUrl: str, timeout: int = _HTTP_CLIENT_TIMEOUT):
        self.__baseUrl = baseUrl
        self.__connector: TCPConnector = TCPConnector(limit=50)
        self.__session: ClientSession = ClientSession(
            self.__baseUrl,
            connector=self.__connector,
            timeout=ClientTimeout(total=timeout),
            raise_for_status=True,
        )

    async def fetch(self, endpoint: str, params: dict):
        try:
            async with self.__session.get(str(endpoint), params=params) as response:
                result = await response.json()
            return result
        except Exception as e:
            # FIXME: report original error?
            raise LookupError(
                f"Unable to get response `{response.content}` for the following request: {str(response.url)}"
            )

    async def close(self):
        if self.__session is not None:
            self.__session.close()
        if self.__connector is not None:
            self.__connector.close()

    async def __call__(self) -> ClientSession:
        if self.__session is None:
            raise Exception(
                f"HTTP client session manager for {self.__baseUrl} not initialized"
            )
        return self.__session
