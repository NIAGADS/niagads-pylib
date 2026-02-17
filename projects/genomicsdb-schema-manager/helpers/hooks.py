import importlib
import pkgutil
from typing import Any, List

from alembic.operations import MigrationScript
from alembic.operations.ops import CreateForeignKeyOp
from helpers.config import Settings
from sqlalchemy import Connection, Table, event, text
from sqlalchemy.schema import ForeignKey


def process_revision_directives(context, revision, directives):
    """
    Alembic callback to modify migration operations before script output.

    Args:
        context: The Alembic migration context, providing access to
            configuration and database state.
        revision: The migration revision identifier.
        directives: A list of migration directives (operations) that
            define what changes Alembic will emit in the migration script.
            Each directive represents a schema operation, such as creating
            or altering tables and constraints. This function can inspect
            and modify these before the migration file is generated.
    """
    strip_foreign_keys_and_defer(context, revision, directives)


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


def strip_foreign_keys_and_defer(
    context: Any,
    revision: str,
    directives: List[Any],
) -> None:
    """
    Alembic autogenerate hook to defer foreign key creation.

    Removes foreign keys from initial table creation and defers them to
    separate CREATE FOREIGN KEY statements.

    This mitigates a a known alembic bug (https://github.com/sqlalchemy/alembic/issues/1059)
    that leads to "table not found" errors when foreign keys reference tables that are
    created later in the same migration.

    Args:
        context (Any): Alembic migration context.
        revision (str): Migration revision identifier.
        directives (List[Any]): List of Alembic migration directives.
    """
    migration: MigrationScript = directives[0]
    deferred_fks = []

    for upgrade_ops in migration.upgrade_ops_list:
        for operation in upgrade_ops.ops[:]:
            if not hasattr(operation, "table"):
                continue

            table: Table = operation.table

            # Collect and remove all foreign keys
            for fk in list(table.foreign_keys):
                deferred_fks.append(
                    {
                        "name": fk.name,
                        "source_table": table.name,
                        "source_schema": table.schema,
                        "source_columns": [col.name for col in fk.parent.columns],
                        "target_table": fk.column.table.name,
                        "target_schema": fk.column.table.schema,
                        "target_column": fk.column.name,
                    }
                )
                table.foreign_keys.discard(fk)

        # Add deferred foreign key creation at the end
        if deferred_fks:
            fk: ForeignKey
            for fk in deferred_fks:
                fk_op = CreateForeignKeyOp(
                    constraint_name=fk["name"],
                    source_table=fk["source_table"],
                    referent_table=fk["target_table"],
                    local_cols=fk["source_columns"],
                    remote_side=[f"{fk['target_table']}.{fk['target_column']}"],
                    source_schema=fk["source_schema"],
                    referent_schema=fk["target_schema"],
                )
                upgrade_ops.ops.append(fk_op)
