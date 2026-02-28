import importlib
import logging
import pkgutil
from helpers.config import Settings
from helpers.types import DBRole
from sqlalchemy import Connection, Table, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


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


def register_catalog_hooks():
    """
    Register global events to catalog schemas and tables in admin.schemacatalog
    and admin.tablecatalog after creation.
    """
    from niagads.genomicsdb.schema.admin.catalog import (
        AdminSchemaCatalog,
        AdminTableCatalog,
    )

    def catalog_schema_creation(schema: str, connection: Connection, **kw):
        """Insert schema entry into admin.schemacatalog after schema creation."""

        with Session(bind=connection) as session:
            schema_entry = (
                session.query(AdminSchemaCatalog).filter_by(name=schema).first()
            )
            if not schema_entry:
                if schema == "admin":
                    raise RuntimeError(
                        "Missing entry for `Admin` schema.  Execute the `admin-bootstrap.sql` file."
                    )
                logger.info(
                    f"New Schema `{schema}` detected. Adding to entry to `Admin.SchemaCatalog`"
                )
                session.add(AdminSchemaCatalog(name=schema))
                session.commit()
        return schema_entry.schema_id

    def catalog_table_creation(target: Table, connection: Connection, **kw):
        """Insert table entry into admin.tablecatalog after table creation."""
        schema = target.schema
        table_name = target.name
        if table_name in ["tablecatalog", "schemacatalog"]:
            with Session(bind=connection) as session:
                table_entry = (
                    session.query(AdminTableCatalog)
                    .filter_by(schema_id=schema_id, name=table_name)
                    .first()
                )
                if not table_entry:
                    raise RuntimeError(
                        f"Missing entry for `{table_name}` schema. "
                        "Execute the `admin-bootstrap.sql` file."
                    )
        try:
            schema_id = catalog_schema_creation(schema, connection)
            with Session(bind=connection) as session:
                session.add(AdminTableCatalog(schema_id=schema_id, name=table_name))
                session.commit()

            logger.info(
                f"New Table `{schema}.{table_name}` detected. Adding to entry to `Admin.TableCatalog`"
            )
        except IntegrityError:
            logger.warning(f"Table '{schema}.{table_name}' already cataloged")

    event.listen(Table, "after_create", catalog_schema_creation)
    event.listen(Table, "after_create", catalog_table_creation)
