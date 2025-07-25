"""Database session management"""

import logging
import asyncpg

# FIXME: write custom error so that we don't need to import fastapi
# just for this in everything that uses
# the database session manager
from fastapi import HTTPException
from niagads.exceptions.core import AbstractMethodNotImplemented, ValidationError
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_scoped_session,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)
from asyncio import current_task

CONNECTION_POOL_SIZE = 10


class DatabaseSessionManager:
    """Dependency for managing database session target based on endpoint
    adapted from: https://dev.to/akarshan/asynchronous-database-sessions-in-fastapi-with-sqlalchemy-1o7e
    """

    def __init__(
        self,
        connection_string: str,
        connectionPoolSize: int = CONNECTION_POOL_SIZE,
        echo: bool = False,
    ):
        """Initialize DatabaseSessionManager object.

        Args:
            connectionString (str): database URI in postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...] format
            connectionPoolSize (int): connection pool size. Defaults to 10
        """
        self.__engine: AsyncEngine = create_async_engine(
            self.__get_async_uri(connection_string),
            echo=echo,  # Log SQL queries for debugging (set to False in production)
            pool_size=connectionPoolSize,  # Maximum number of permanent connections to maintain in the pool
            max_overflow=10,  # Maximum number of additional connections that can be created if the pool is exhausted
            pool_timeout=30,  # Number of seconds to wait for a connection if the pool is exhausted
            pool_recycle=1800,  # Maximum age (in seconds) of connections that can be reused
        )

        self.__sessionMaker: async_sessionmaker = async_sessionmaker(bind=self.__engine)
        self.__session: AsyncSession = async_scoped_session(
            self.__sessionMaker, scopefunc=current_task
        )
        self.logger = logging.getLogger(__name__)
        logging.getLogger("sqlalchemy").setLevel(logging.ERROR)  # turn off INFO logging
        logging.getLogger("sqlalchemy.engine").setLevel(
            logging.ERROR
        )  # turn off INFO logging

    def __get_async_uri(self, uri: str = None):
        return uri.replace("postgresql:", "postgresql+asyncpg:")

    def get_engine(self):
        return self.__engine

    async def close(self):
        """
        This does not actually disconnect from the database,
        but closes all pooled connections and then creates a fresh connection pool
        (i.e. takes care of dangling sessions)
        SQL alchmeny should handle the disconnect on exit
        """
        if self.__engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self.__engine.dispose()

    async def __call__(self):
        session: AsyncSession  # annotated type hint
        async with self.__session() as session:
            if session is None:
                raise Exception("DatabaseSessionManager is not initialized")

            try:
                # await session.execute(text("SELECT 1"))
                yield session

            except (
                NotImplementedError,
                AbstractMethodNotImplemented,
                ValidationError,
                RuntimeError,
                HTTPException,
            ) as err:
                if isinstance(err, AbstractMethodNotImplemented):
                    raise NotImplementedError(str(err))
                else:
                    raise err

            except (
                asyncpg.InvalidPasswordError,
                ConnectionRefusedError,
                ConnectionError,
            ) as err:
                self.logger.error("Database Error", exc_info=err, stack_info=True)
                raise OSError(f"Database Error: {str(err)}")

            except Exception as err:
                # everything else for which we currently have no handler
                if "Connection refused" in str(err) or "Connection" in str(type(err)):
                    # don't want to create dependency to redis in this module
                    # so checking message instead of exception type
                    self.logger.error("Database Error", exc_info=err, stack_info=True)
                    raise OSError(f"Database Error: {str(err)}")

                self.logger.error("Unexpected Error", exc_info=err, stack_info=True)
                raise RuntimeError(f"Unexpected Error: {str(err)}")

            finally:
                await session.rollback()
                await session.close()
