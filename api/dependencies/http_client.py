from aiohttp import ClientSession
from aiohttp.connector import TCPConnector

class HttpClientSessionManager():
    """ Wrapper functions for FILER API, to help standardize, validate calls and protect from attacks """
    
    def __init__(self, baseUrl):
        self.__baseUrl = baseUrl
        self.__connector: TCPConnector = TCPConnector(limit=50)    
        
    async def close(self):
        if self.__connector is not None:
            self.__connector.close()
            
    async def __call__(self):
        session: ClientSession # annotated type hint
        async with ClientSession(self.__baseUrl, connector=self.__connector, raise_for_status=True) as session:
            if session is None:
                raise Exception(f"HTTP client session manager for {self.__baseUrl} not initialized")
            try: 
                yield session
            finally:
                await session.close()