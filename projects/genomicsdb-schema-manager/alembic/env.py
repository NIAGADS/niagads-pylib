import asyncio
from logging.config import fileConfig

from alembic import context
from niagads.database.session import DatabaseSessionManager
from sqlalchemy import text
from sqlalchemy.engine import Connection

from database.genomicsdb.schemas import Schema
from database.config import Settings

# get config options from the .ini file
# including logging config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_target_metadata():
    xArgs = context.get_x_argument(as_dictionary=True)
    schema = xArgs.get("schema", None)
    return Schema.base(schema).metadata


# has to be a global so that include_* hooks can access
# see alembic docs:
# https://alembic.sqlalchemy.org/en/latest/autogenerate.html#omitting-table-names-from-the-autogenerate-process
TARGET_METADATA = get_target_metadata()


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == TARGET_METADATA.schema
    else:
        return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """

    context.configure(
        url=Settings.from_env().DATABASE_URI,
        target_metadata=TARGET_METADATA,
        include_schemas=True,
        include_name=include_name,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:

    context.configure(
        connection=connection,
        target_metadata=TARGET_METADATA,
        include_schemas=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        # context.execute(text(f"SET search_path TO {TARGET_METADATA.schema}"))
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    SessionManager = DatabaseSessionManager(
        connection_string=Settings.from_env().DATABASE_URI
    )

    connectable = SessionManager.get_engine()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
