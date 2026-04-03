"""Query and display external database references from the database."""

import argparse

from niagads.common.core import ComponentBaseMixin
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.session import DatabaseSessionManager
from niagads.settings.core import CustomSettings
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound


class Settings(CustomSettings):
    """Application settings."""

    DATABASE_URI: str


class XDBRefLookup(ComponentBaseMixin):
    """Query and display external database references."""

    def __init__(
        self, database_uri: str = None, debug: bool = False, verbose: bool = False
    ):
        """
        Initialize the lookup service.

        Args:
            database_uri (str, optional): PostgreSQL connection URI. If not provided,
                reads from DATABASE_URI environment variable.
        """
        super().__init__(debug=debug, verbose=verbose)

        self._database_uri = (
            database_uri if database_uri else Settings.from_env().DATABASE_URI
        )
        self._session_manager = DatabaseSessionManager(self._database_uri)

    async def run(self, db_name: str) -> list[dict]:
        """
        Retrieve external database references by name.

        Args:
            db_name (str): Database name to search for.

        Returns:
            list[dict]: List of dictionaries with 'name' and 'version' keys.

        Raises:
            RuntimeError: If database connection fails.
        """

        async with self._session_manager.session_ctx() as session:
            stmt = select(ExternalDatabase.name, ExternalDatabase.version).where(
                or_(
                    ExternalDatabase.name.ilike(f"%{db_name}%"),
                    ExternalDatabase.database_key == db_name.upper(),
                )
            )
            result = (await session.execute(stmt)).mappings().all()
            return result


async def main():
    """Entry point for running as a script."""
    parser = argparse.ArgumentParser(
        description="Query external database references by name",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--xdb",
        required=True,
        metavar="XDB_NAME",
        help="external database name to query (case insensitive)",
    )
    parser.add_argument(
        "--databaseUri",
        help="PostgreSQL connection URI; if not set, reads DATABASE_URI from environment or .env",
    )

    args = parser.parse_args()

    lookup_service = XDBRefLookup(database_uri=args.databaseUri)

    try:
        matches = await lookup_service.run(args.xdb)
        for xdb in matches:
            print(f"{xdb['name']}|{xdb['version']}")

    except NoResultFound:
        print(f"No external database references found matching {args.xdb}")


def run_main():
    """wrapper necessary so that the main coroutine gets correctly awaited"""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run_main()
