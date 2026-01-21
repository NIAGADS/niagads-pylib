import asyncio
from logging.config import fileConfig

from alembic import context
from helpers.config import Settings
from helpers.hooks import register_schema_creation, register_schemas
from helpers.migration_context import MigrationContext
from niagads.database import DatabaseSessionManager
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

# register hooks
register_schemas()
register_schema_creation()

# get config options from the .ini file
# including logging config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

migration_ctx: MigrationContext = MigrationContext()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    migration_ctx.run_migrations_offline()


def do_run_migrations(connection: Connection) -> None:
    migration_ctx.do_run_migrations(connection)


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    SessionManager: DatabaseSessionManager = DatabaseSessionManager(
        connection_string=Settings.from_env().DATABASE_URI
    )

    connectable: AsyncEngine = SessionManager.get_engine()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
