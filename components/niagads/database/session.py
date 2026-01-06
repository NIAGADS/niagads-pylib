"""Database session management"""

from contextlib import asynccontextmanager
import logging
from asyncio import current_task

import asyncpg

from niagads.exceptions.core import AbstractMethodNotImplemented, ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

CONNECTION_POOL_SIZE = 10


class DatabaseSessionManager:
    """Dependency for managing database session target based on endpoint
    adapted from: https://dev.to/akarshan/asynchronous-database-sessions-in-fastapi-with-sqlalchemy-1o7e
    """

    def __init__(
        self,
        connection_string: str,
        pool_size: int = CONNECTION_POOL_SIZE,
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
            pool_size=pool_size,  # Maximum number of permanent connections to maintain in the pool
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

    def __get_async_uri(self, uri: str = None) -> str:
        """Convert a standard PostgreSQL URI to an asyncpg-compatible URI.

        Args:
            uri (str, optional): The PostgreSQL URI. Defaults to None.

        Returns:
            str: The asyncpg-compatible PostgreSQL URI.
        """
        return uri.replace("postgresql:", "postgresql+asyncpg:")

    @property
    def engine(self) -> AsyncEngine:
        """Get the SQLAlchemy async engine.

        Returns:
            AsyncEngine: The SQLAlchemy async engine instance.
        """
        return self.__engine

    async def test_connection(self) -> bool:
        """Test the database connection by executing a simple SELECT 1 query.

        Returns:
            bool: True if the connection is successful.

        Raises:
            OSError: If the connection test fails.
        """
        try:
            async with self.__engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as err:
            self.logger.error(
                "Database connection test failed", exc_info=True, stack_info=True
            )
            raise OSError(f"Database connection test failed: {str(err)}")

    async def close(self) -> None:
        """Close all pooled connections and reset the connection pool.

        Raises:
            Exception: If the engine is not initialized.
        """
        if self.__engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self.__engine.dispose()

    @asynccontextmanager
    async def session_ctx(self):
        """
        Provide an async context manager for a SQLAlchemy async session.

        Yields:
            AsyncSession: An active SQLAlchemy async session.

        Raises:
            RuntimeError: If the session manager is not initialized.

        Example:
            async with manager.session_ctx() as session:
                await session.execute(...)
        """
        session: AsyncSession  # annotated type hint
        async with self.__session() as session:
            if session is None:
                raise RuntimeError("DatabaseSessionManager is not initialized")
            try:
                yield session
            finally:
                if hasattr(session, "in_transaction") and session.in_transaction():
                    await session.rollback()
                if session.is_active:
                    await session.close()

    async def __call__(self):
        """Provide an async database session; cannot be used as a context manager.

        Yields:
            AsyncSession: The SQLAlchemy async session.

        Raises:
            OSError: For database connection errors.
            RuntimeError: For errors propogated up from calling functions.
        """
        session: AsyncSession  # annotated type hint
        async with self.__session() as session:
            if session is None:
                raise RuntimeError("DatabaseSessionManager is not initialized")

            try:
                yield session

            except (
                NotImplementedError,
                AbstractMethodNotImplemented,
                ValidationError,
                RuntimeError,
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
                self.logger.error("Database Error", exc_info=True, stack_info=True)
                raise OSError(f"Database Error: {str(err)}")

            except Exception as err:
                if "HTTPException" in type(err).__name__ or getattr(
                    err, "status_code", False
                ):
                    raise err  # will be handled by API
                # everything else for which we currently have no handler
                if "Connection refused" in str(err) or "Connection" in str(type(err)):
                    # don't want to create dependency to redis in this module
                    # so checking message instead of exception type
                    self.logger.error("Database Error", exc_info=True, stack_info=True)
                    raise OSError(f"Database Error: {str(err)}")

                self.logger.error("Unexpected Error", exc_info=True, stack_info=True)
                raise RuntimeError(f"Unexpected Error: {str(err)}")

            finally:
                # Only rollback if transaction is active and session is not closed
                if hasattr(session, "in_transaction") and session.in_transaction():
                    await session.rollback()
                if session.is_active:
                    await session.close()
