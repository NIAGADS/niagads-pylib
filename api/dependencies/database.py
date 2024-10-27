# Middleware for choosing database based on endpoint
# adapted from: https://dev.to/akarshan/asynchronous-database-sessions-in-fastapi-with-sqlalchemy-1o7e
import logging
from fastapi.exceptions import RequestValidationError
from sqlmodel import text
from sqlalchemy.ext.asyncio import create_async_engine, async_scoped_session, AsyncSession, AsyncEngine, async_sessionmaker
from asyncio import current_task

from api.internal.config import get_settings

logger = logging.getLogger(__name__)
class DatabaseSessionManager:
    def __init__(self, route: str):
        self.__connectionString: str = self.__get_db_url(route)
        self.__engine: AsyncEngine = create_async_engine(
            self.__connectionString, 
            echo=True,  # Log SQL queries for debugging (set to False in production)
            pool_size=10,  # Maximum number of permanent connections to maintain in the pool
            max_overflow=10,  # Maximum number of additional connections that can be created if the pool is exhausted
            pool_timeout=30,  # Number of seconds to wait for a connection if the pool is exhausted
            pool_recycle=1800  # Maximum age (in seconds) of connections that can be reused                                
        )
        
        self.__sessionMaker: async_sessionmaker = async_sessionmaker(bind = self.__engine)
        self.__session: AsyncSession = async_scoped_session(
            self.__sessionMaker,
            scopefunc=current_task
        )
        
    
    def __get_db_url(self, route: str = None):
        match route:
            case 'genomics':
                return get_settings().GENOMICSDB_URL.replace('postgresql:', 'postgresql+asyncpg:')
            case 'cache':
                return get_settings().API_CACHEDB_URL
            case 'metadata': 
                return get_settings().API_STATICDB_URL.replace('postgresql:', 'postgresql+asyncpg:')
            case _:
                raise RuntimeError('Need to specify endpoint database - one of: genomics, cache, or metadata')
            
    async def close(self):
        """ 
            note: this does not actually disconnect from the db, 
            but closes all pooled connections and then creates a fresh connection pool
            (i.e. takes care of dangling sessions)
            SQL alchmeny should handle the disconnect on exit
        """
        if self.__engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        self.__engine.dispose()
        

    async def __call__(self):
        session: AsyncSession # annotated type hint
        async with self.__session() as session:
            if session is None:
                raise Exception("DatabaseSessionManager is not initialized")
            try: 
                await session.execute(text("SELECT 1"))
                yield session
            except (NotImplementedError, RequestValidationError, RuntimeError):
                await session.rollback()
                raise  
            except Exception as err:
                # everything else for which we currently have no handler
                await session.rollback()
                logger.error('Unexpected Error', exc_info=err, stack_info=True)
                raise RuntimeError(f'Unexpected Error: {str(err)}')
            finally:
                await session.close()