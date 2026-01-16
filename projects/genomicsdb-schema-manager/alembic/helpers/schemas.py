# schema_helpers.py

from enum import Enum

# note the schema base is imported from `core`, which contains both the base and the models
# not `base`, which just defines the base; this ensures all tables are generated
# see https://stackoverflow.com/a/77767002
from niagads.genomicsdb.schema.admin.core import AdminSchemaBase
from niagads.genomicsdb.schema.dataset.core import DatasetSchemaBase
from niagads.genomicsdb.schema.gene.core import GeneTableBase
from niagads.genomicsdb.schema.reference.core import ReferenceSchemaBase
from niagads.genomicsdb.schema.variant.core import VariantSchemaBase
from sqlalchemy import Connection, MetaData, Table, event
from sqlalchemy.orm import DeclarativeBase


def register_schema_creation():
    """Register global event to auto-create schemas for tables with .schema set."""

    def ensure_schema(target: Table, connection: Connection, **kw):
        schema = target.schema
        if schema:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    event.listen(Table, "before_create", ensure_schema)


class Schema(Enum):
    ADMIN = AdminSchemaBase
    REFERENCE = ReferenceSchemaBase
    DATASET = DatasetSchemaBase
    VARIANT = VariantSchemaBase
    GENE = GeneTableBase
    ALL = "ALL"

    @classmethod
    def _missing_(cls, value: str):
        if value is None or value == "":
            raise ValueError(
                "Schema value cannot be None; please run alembic with x argument: alembic -x schema=<schema_name>.  To run on all schemas, set schema=ALL.  To run on a subset of schemas, provide a comma separated list, e.g. schema=ADMIN,GENE"
            )
        try:
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
        except ValueError as err:
            raise err

    @classmethod
    def base(cls, schema: str) -> DeclarativeBase:
        """
        Return the Declarative Base class for the given schema name or enum member.
        If schema is not 'ALL', returns the Declarative Base for the specified schema.
        If schema is 'ALL', raises RuntimeError (use metadata() for all bases).

        Args:
            schema (str or Schema): The schema name or enum member.

        Returns:
            DeclarativeBase: The base class for the schema.

        Raises:
            RuntimeError: If schema is 'ALL'.
        """
        if not cls.is_all(schema):
            return cls(schema).value
        else:
            raise RuntimeError(
                "Schema set to `ALL` - unable to retrieve Declarative Base class"
            )

    @classmethod
    def metadata(cls, schema: str) -> list[MetaData]:
        """
        Return the SQLAlchemy MetaData object(s) for the given schema name(s) or enum member(s).

        - If schema is 'ALL', returns a list of MetaData objects for all schemas except 'ALL'.
        - If schema is a comma-separated string (e.g. 'ADMIN,GENE'), returns MetaData objects for each listed schema.
        - If schema is a specific schema name or enum member, returns a single-element list containing its MetaData.

        Args:
            schema (str or Schema): The schema name(s) or enum member(s).

        Returns:
            list[MetaData]: List of MetaData objects for the schema(s).
        """
        if cls.is_all(schema):
            return [member.value.metadata for member in cls if member != cls.ALL]
        elif "," in schema:
            return [cls(member.strip()).value.metadata for member in schema.split(",")]
        else:
            return [cls(schema).value.metadata]

    @classmethod
    def is_all(cls, schema: str) -> bool:
        """
        Check if the given schema argument represents 'ALL'.

        Args:
            schema (str or Schema): The schema name or enum member.

        Returns:
            bool: True if schema is 'ALL', False otherwise.
        """
        return schema == cls.ALL or (
            isinstance(schema, str) and schema.upper() == "ALL"
        )
