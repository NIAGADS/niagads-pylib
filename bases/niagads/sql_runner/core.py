#!/usr/bin/env python3
"""SQL file runner.

Loads and executes SQL from a file against a PostgreSQL database using
the `DatabaseSessionManager` for async session management.

Can be run as a script or imported as a module.
"""

import logging
from pathlib import Path

from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.settings.core import CustomSettings
from niagads.utils.logging import LOG_FORMAT_STR, ExitOnExceptionHandler


class Settings(CustomSettings):
    DATABASE_URI: str


class SqlRunner(ComponentBaseMixin):
    """Loads and executes SQL from a file against a PostgreSQL database.

    Uses `DatabaseSessionManager.raw_connection()` to bypass SQLAlchemy's
    prepared statement protocol, supporting multi-statement SQL files and
    PL/pgSQL function definitions.

    Rolls back by default; pass `commit=True` to persist changes.

    Example:
        runner = SqlRunner("path/to/script.sql", connection_string, commit=True)
        await runner.run()
    """

    def __init__(
        self,
        sql_file: str,
        connection_string: str,
        commit: bool = False,
        debug: bool = False,
    ):
        """Initialize the SqlRunner.

        Args:
            sql_file (str): Full path to the SQL file to execute.
            connection_string (str): PostgreSQL connection URI.
            commit (bool): Commit the transaction if True; roll back otherwise. Defaults to False.
            debug (bool): Enable SQLAlchemy query logging. Defaults to False.

        Raises:
            FileNotFoundError: If the SQL file does not exist.
            ValueError: If the SQL file is empty.
        """
        super().__init__(debug=debug)

        self.__sql_file = Path(sql_file)
        self.__connection_string = connection_string
        self.__commit = commit

        if not self.__sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file}")

        self.__sql = self.__sql_file.read_text(encoding="utf-8").strip()
        if not self.__sql:
            raise ValueError(f"SQL file is empty: {sql_file}")

    def __repr__(self) -> str:
        return f"SqlRunner(file={self.__sql_file}, commit={self.__commit}, debug={self._debug})"

    async def run(self) -> None:
        """Execute the SQL file contents against the database.

        Raises:
            OSError: If the database connection fails.
            RuntimeError: If SQL execution fails.
        """
        manager = DatabaseSessionManager(
            self.__connection_string, echo=self._debug, pool_size=1
        )

        try:
            async with manager.raw_connection() as conn:
                self.logger.info(f"Executing SQL from: {self.__sql_file}")

                if self.__commit:
                    await conn.execute(self.__sql)
                    self.logger.info("Transaction committed.")
                else:
                    async with conn.transaction():
                        await conn.execute(self.__sql)
                        raise Exception("dry-run rollback")

        except Exception as err:
            if "dry-run rollback" in str(err):
                self.logger.info("Transaction rolled back (dry-run).")
            else:
                raise

        finally:
            await manager.close()


async def run():
    """Entry point for running the SQL runner as a script."""
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--file",
        required=True,
        metavar="SQL_FILE",
        help="full path to the SQL file to execute",
    )
    parser.add_argument(
        "--databaseUri",
        help="PostgreSQL connection URI; if not set, reads DATABASE_URI from .env",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="commit the transaction; rolls back by default (dry-run)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable SQLAlchemy query logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        handlers=[ExitOnExceptionHandler()],
        format=LOG_FORMAT_STR,
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    connection_string = (
        args.databaseUri
        if args.databaseUri is not None
        else Settings.from_env().DATABASE_URI
    )

    runner = SqlRunner(
        sql_file=args.file,
        connection_string=connection_string,
        commit=args.commit,
        debug=args.debug,
    )

    await runner.run()


def main():
    """Wrapper so that the main coroutine is correctly awaited."""
    import asyncio

    asyncio.run(run())


if __name__ == "__main__":
    main()
