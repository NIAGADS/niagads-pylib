import importlib
import pkgutil

from sqlalchemy import Connection, Table, event
from helpers.constants import SCHEMA_PACKAGES
from helpers.config import Settings


def register_schemas():
    """
    Dynamically import all modules in the given schema packages
    to trigger schema registration.
    """
    package = importlib.import_module(Settings.from_env().SCHEMA_DEFS)
    for _, modname, ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        if not ispkg:
            importlib.import_module(modname)


def register_schema_creation():
    """Register global event to auto-create schemas for tables with .schema set."""

    def ensure_schema(target: Table, connection: Connection, **kw):
        schema = target.schema
        if schema:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    event.listen(Table, "before_create", ensure_schema)
