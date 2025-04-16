"""Database session management"""

import logging
import asyncpg
from fastapi.exceptions import RequestValidationError
from niagads.open_access_api_configuration.constants import CONNECTION_POOL_SIZE
from niagads.open_access_api_configuration.core import get_settings
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_scoped_session,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)
from asyncio import current_task


class DatabaseSessionManager:
    """Dependency for managing database session target based on endpoint
    adapted from: https://dev.to/akarshan/asynchronous-database-sessions-in-fastapi-with-sqlalchemy-1o7e
    """

    def __init__(self):
        """Initialize DatabaseSessionManager object.

        Args:
            uri (str): database URI in postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...] format
        """
        connectionString: str = self.__get_async_uri(get_settings().API_APP_DB_URI)
        self.__engine: AsyncEngine = create_async_engine(
            connectionString,
            echo=True,  # Log SQL queries for debugging (set to False in production)
            pool_size=CONNECTION_POOL_SIZE,  # Maximum number of permanent connections to maintain in the pool
            max_overflow=10,  # Maximum number of additional connections that can be created if the pool is exhausted
            pool_timeout=30,  # Number of seconds to wait for a connection if the pool is exhausted
            pool_recycle=1800,  # Maximum age (in seconds) of connections that can be reused
        )

        self.__sessionMaker: async_sessionmaker = async_sessionmaker(bind=self.__engine)
        self.__session: AsyncSession = async_scoped_session(
            self.__sessionMaker, scopefunc=current_task
        )
        self.logger = logging.getLogger(__name__)

    def __get_async_uri(self, uri: str = None):
        return uri.replace("postgresql:", "postgresql+asyncpg:")

    async def close(self):
        """
        This does not actually disconnect from the database,
        but closes all pooled connections and then creates a fresh connection pool
        (i.e. takes care of dangling sessions)
        SQL alchmeny should handle the disconnect on exit
        """
        if self.__engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        self.__engine.dispose()

    async def __call__(self):
        session: AsyncSession  # annotated type hint
        async with self.__session() as session:
            if session is None:
                raise Exception("DatabaseSessionManager is not initialized")
            try:
                # await session.execute(text("SELECT 1"))
                yield session
            except (NotImplementedError, RequestValidationError, RuntimeError):
                await session.rollback()
                raise
            except asyncpg.InvalidPasswordError as err:
                await session.rollback()
                self.logger.error("Database Error", exc_info=err, stack_info=True)
                raise OSError(f"Database Error")
            except Exception as err:
                # everything else for which we currently have no handler
                await session.rollback()
                self.logger.error("Unexpected Error", exc_info=err, stack_info=True)
                raise RuntimeError(f"Unexpected Error: {str(err)}")
            finally:
                await session.close()
