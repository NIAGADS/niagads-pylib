import importlib
import pkgutil
from helpers.config import Settings
from helpers.types import DBRole
from sqlalchemy import Connection, Table, event, text


def register_schemas():
    """
    Dynamically import all modules in the given schema packages
    to trigger schema registration.
    """
    package = importlib.import_module(Settings.from_env().SCHEMA_DEFS)
    for _, modname, ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        if not ispkg and modname.endswith(".core"):
            importlib.import_module(modname)


def register_schema_creation():
    """Register global event to auto-create schemas for tables with .schema set."""

    def ensure_schema(target: Table, connection: Connection, **kw):
        schema = target.schema
        if schema:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    event.listen(Table, "before_create", ensure_schema)


def register_schema_permissions(role: DBRole, read_only: bool = False):
    """
    Register global event to grant permissions on schemas when created.

    Args:
        role: Database role name to grant permissions to
        read_only: If True, grant SELECT only; if False, grant SELECT, INSERT, UPDATE, DELETE
    """

    def grant_permissions_on_creation(target: Table, connection: Connection, **kw):
        schema = target.schema
        if schema:
            # Grant schema usage
            connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO {role}'))

            # Grant function usage
            connection.execute(
                text(
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                    f"GRANT EXECUTE ON FUNCTIONS TO {role}"
                )
            )

            if read_only:
                connection.execute(
                    text(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                        f"GRANT SELECT ON TABLES TO {role}"
                    )
                )

            else:
                connection.execute(
                    text(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
                    )
                )

                connection.execute(
                    text(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                        f"GRANT USAGE, SELECT ON SEQUENCES TO {role}"
                    )
                )

    event.listen(Table, "before_create", grant_permissions_on_creation)
