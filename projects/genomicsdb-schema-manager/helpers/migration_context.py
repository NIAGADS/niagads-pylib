from alembic import context
from niagads.genomicsdb.schema.registry import SchemaRegistry
from helpers.config import Settings
from sqlalchemy import Connection, MetaData
from typing import List, Any


class MigrationContext:
    def __init__(self):
        xArgs: dict = context.get_x_argument(as_dictionary=True)
        schema: str = xArgs.get("schema", "")
        self.__schema_independent: bool = True if schema.upper() == "NONE" else False

        self.__target_schema_metadata: List[MetaData] = (
            [MetaData()]
            if self.__schema_independent
            else (
                SchemaRegistry.get_registered_metadata()
                if schema.upper() == "ALL"
                else [SchemaRegistry.get_schema_metadata(schema)]
            )
        )

    def include_name(self, name: str, type_: str, parent_names: Any) -> bool:
        if self.__schema_independent:
            return True
        if type_ == "schema":
            return name in self.__target_schema_metadata
        return type_ != "schema"

    def run_migrations_offline(self) -> None:
        for metadata in self.__target_schema_metadata:
            config_kwargs = {
                "url": Settings.from_env().DATABASE_URI,
                "target_metadata": metadata,
                "literal_binds": True,
                "dialect_opts": {"paramstyle": "named"},
            }
            if not self.__schema_independent:
                config_kwargs["include_schemas"] = True
                config_kwargs["include_name"] = self.include_name

            context.configure(**config_kwargs)
            with context.begin_transaction():
                context.run_migrations()

    def do_run_migrations(self, connection: Connection) -> None:
        for metadata in self.__target_schema_metadata:
            config_kwargs = {
                "connection": connection,
                "target_metadata": metadata,
            }
            if not self.__schema_independent:
                config_kwargs["include_schemas"] = True
                config_kwargs["include_name"] = self.include_name

            context.configure(**config_kwargs)
            with context.begin_transaction():
                context.run_migrations()
