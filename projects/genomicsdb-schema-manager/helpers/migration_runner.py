from typing import Any, List

from alembic import context
from helpers.config import Settings
from sqlalchemy import Connection
from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase


class MigrationRunner:
    def __init__(self):
        xArgs: dict = context.get_x_argument(as_dictionary=True)
        schema: str = xArgs.get("schema", None)
        self.__skip_fks = "skipForeignKeys" in xArgs
        self.__schema_independent: bool = True if schema is None else False

        self.__target_schema: List[str] = (
            None
            if self.__schema_independent
            else (
                self.__get_all_schemas()
                if schema.lower() == "all"
                else [schema.lower()] if self.is_valid_schema(schema) else None
            )
        )

    def __get_all_schemas(self) -> List[str]:
        """Dynamically extract all schemas from GenomicsDBSchemaBase registry."""
        schemas = []
        for mapper in GenomicsDBSchemaBase.registry.mappers:
            table = mapper.class_.__table__
            if hasattr(table, "schema") and table.schema:
                schemas.append(table.schema)
        return list(set(schemas))  # Remove duplicates

    def is_valid_schema(self, schema: str) -> bool:
        """Check if a schema string is a valid schema in GenomicsDBSchemaBase."""
        valid_schemas = self.__get_all_schemas()
        if schema.lower() in valid_schemas:
            return True
        else:
            raise ValueError(f"Schema {schema} is invalid for the GenomicsDB")

    def include_name(self, name: str, type_: str, parent_names: Any) -> bool:
        # adapted to allow affect registered schemas, except when
        # schema-independent (e.g., create extension) commands are
        # executed
        if self.__schema_independent:
            return True
        if type_ == "schema":
            return name in self.__target_schema
        return type_ != "schema"

    def include_object(
        self, object_, name: str, type_: str, reflected: bool, compare_to: Any
    ) -> bool:
        """
        Alembic context filter
        adapted to exclude foreign keys from migrations that require
        fks not yet created, generating w/out FKs, then upgrading, then running
        migration again w/out excluding FKs should bypass the alembic bug
        """
        # print(f"include_object: name={name}, type_={type_}, skip_fks={self.__skip_fks}")
        if self.__skip_fks and type_ == "foreign_key_constraint":
            return False

        if type_ == "table" and getattr(object_, "is_view", False):
            return False

    def run_migrations_offline(self) -> None:
        config_kwargs = {
            "url": Settings.from_env().DATABASE_URI,
            "target_metadata": GenomicsDBSchemaBase.metadata,
            "literal_binds": True,
            "dialect_opts": {"paramstyle": "named"},
        }
        if not self.__schema_independent:
            config_kwargs |= {
                "include_schemas": True,
                "include_name": self.include_name,
                "include_object": self.include_object,
            }

        context.configure(**config_kwargs)
        with context.begin_transaction():
            context.run_migrations()

    def do_run_migrations(self, connection: Connection) -> None:

        config_kwargs = {
            "connection": connection,
            "target_metadata": GenomicsDBSchemaBase.metadata,
        }
        if not self.__schema_independent:
            config_kwargs |= {
                "include_schemas": True,
                "include_name": self.include_name,
                "include_object": self.include_object,
            }

        context.configure(**config_kwargs)
        with context.begin_transaction():
            context.run_migrations()
