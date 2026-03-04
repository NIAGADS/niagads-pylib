from typing import Any, List

from alembic import context
from helpers.config import Settings
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import Connection, MetaData


class MigrationContext:
    def __init__(self):
        xArgs: dict = context.get_x_argument(as_dictionary=True)
        schema: str = xArgs.get("schema", None)
        self.__skip_fks = "skipForeignKeys" in xArgs
        self.__schema_independent: bool = True if schema is None else False

        self.__target_metadata: List[MetaData] = (
            [MetaData()]
            if self.__schema_independent
            else (
                SchemaRegistry.get_registered_metadata()
                if schema.upper() == "ALL"
                else [SchemaRegistry.get_schema_metadata(schema)]
            )
        )

        self.__target_schema: List[str] = (
            None
            if self.__schema_independent
            else [metadata.schema for metadata in self.__target_metadata]
        )

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
        print(f"include_object: name={name}, type_={type_}, skip_fks={self.__skip_fks}")
        if self.__skip_fks and type_ == "foreign_key_constraint":
            return False

        # Skip objects (tables, constraints, etc.) related to materialized views
        if hasattr(object_, "table") and object_.table.name.endswith("_mv"):
            return False
        if type_ == "table" and name.endswith("_mv"):
            return False
        return True

    def run_migrations_offline(self) -> None:
        for metadata in self.__target_metadata:
            config_kwargs = {
                "url": Settings.from_env().DATABASE_URI,
                "target_metadata": metadata,
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
        for metadata in self.__target_metadata:
            config_kwargs = {
                "connection": connection,
                "target_metadata": metadata,
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
