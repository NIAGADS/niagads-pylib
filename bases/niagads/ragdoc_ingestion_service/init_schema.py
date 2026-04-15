import asyncio

from sqlalchemy import text

from niagads.database.ragdoc.schema import RAGDeclarativeBase
from niagads.database.session import DatabaseSessionManager
from niagads.settings.core import CustomSettings
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field


class Settings(CustomSettings):
    DATABASE_URI: str = Field(..., pattern=RegularExpressions.POSTGRES_URI)


async def initialize_schema():
    """Initialize database extensions and ORM-managed tables."""
    settings = Settings.from_env()
    manager = DatabaseSessionManager(settings.DATABASE_URI)

    try:
        async with manager.engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(RAGDeclarativeBase.metadata.create_all)
    finally:
        await manager.close()


def main():
    """Run schema initialization."""
    asyncio.run(initialize_schema())


if __name__ == "__main__":
    main()
