import importlib
import logging
import pkgutil
from helpers.config import Settings
from helpers.types import DBRole
from sqlalchemy import Connection, Table, event, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
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


def inject_schema_creation_directives(context, revision, directives):
    """
    Alembic process_revision_directives callback to inject CREATE SCHEMA statements.
    Extracts schemas from metadata.schema (not table.schema) and injects them
    at the beginning of the upgrade operations.
    """
    from alembic.operations import ops

    # Skip if no operations
    if not directives or directives[0].upgrade_ops.is_empty():
        return

    # Get target_metadata from context
    target_metadata = context.opts.get("target_metadata")
    if not target_metadata:
        return

    # Collect unique schemas from metadata objects
    metadata_list = (
        target_metadata if isinstance(target_metadata, list) else [target_metadata]
    )
    schemas = set()
    for metadata in metadata_list:
        schema = getattr(metadata, "schema", None)
        if schema:
            schemas.add(schema)

    # Inject CREATE SCHEMA statements at the beginning
    if schemas:
        # Insert CREATE SCHEMA and COMMIT for each schema at the beginning
        for schema in sorted(schemas):
            # prepending each
            directives[0].upgrade_ops.ops.insert(0, ops.ExecuteSQLOp("COMMIT"))
            directives[0].upgrade_ops.ops.insert(
                0, ops.ExecuteSQLOp(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            )


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
        SchemaCatalog,
        TableCatalog,
    )

    def catalog_schema_creation(schema: str, connection: Connection, **kw):
        """Insert schema entry into admin.schemacatalog after schema creation."""

        with Session(bind=connection) as session:
            schema_id = (
                session.query(SchemaCatalog.schema_id).filter_by(name=schema).first()
            )

            if not schema_id:
                logger.info(
                    f"New Schema `{schema}` detected. Adding to entry to `Admin.SchemaCatalog`"
                )
                schema_entry = SchemaCatalog(name=schema)
                session.add(schema_entry)
                session.commit()
                schema_id = schema_entry.schema_id
                return schema_id
            else:
                return schema_id[0]

    def catalog_table_creation(target: Table, connection: Connection, **kw):
        """Insert table entry into admin.tablecatalog after table creation."""
        schema = target.schema
        table_name = target.name

        if schema.lower() == "admin":
            return

        schema_id = catalog_schema_creation(schema, connection)

        with Session(bind=connection) as session:
            try:
                table_entry = (
                    session.query(TableCatalog)
                    .filter_by(schema_id=schema_id, name=table_name)
                    .first()
                )
                if not table_entry:
                    # sqlalchemy will have long thrown a missing pk error
                    # so can assume it exists
                    pk_field = target.primary_key.columns[0]
                    session.add(
                        TableCatalog(
                            schema_id=schema_id,
                            name=table_name,
                            table_primary_key=pk_field.name,
                        )
                    )
                    session.commit()

                    logger.info(
                        f"New Table `{schema}.{table_name}` detected. "
                        f"Adding to entry to `Admin.TableCatalog` with primary key `{pk_field}`"
                    )
            except IntegrityError:
                logger.warning(f"Table '{schema}.{table_name}' already cataloged")
                session.rollback()

    event.listen(Table, "after_create", catalog_table_creation)
