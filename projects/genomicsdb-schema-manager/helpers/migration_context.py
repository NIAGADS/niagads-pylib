from alembic import context
from niagads.genomicsdb.schema.core import Schema
from helpers.config import Settings
from sqlalchemy import Connection, MetaData
from typing import List, Any


class MigrationContext:
    def __init__(self):
        xArgs: dict = context.get_x_argument(as_dictionary=True)
        schema: str = xArgs.get("schema", "")
        self.__target_schema_metadata: List[MetaData] = Schema.metadata(schema)

    def include_name(self, name: str, type_: str, parent_names: Any) -> bool:
        if type_ == "schema":
            return name in self.__target_schema_metadata
        return type_ != "schema"

    def run_migrations_offline(self) -> None:
        for metadata in self.__target_schema_metadata:
            context.configure(
                url=Settings.from_env().DATABASE_URI,
                target_metadata=metadata,
                include_schemas=True,
                include_name=self.include_name,
                literal_binds=True,
                dialect_opts={"paramstyle": "named"},
            )
            with context.begin_transaction():
                context.run_migrations()

    def do_run_migrations(self, connection: Connection) -> None:
        for metadata in self.__target_schema_metadata:
            context.configure(
                connection=connection,
                target_metadata=metadata,
                include_schemas=True,
                include_name=self.include_name,
            )
            with context.begin_transaction():
                context.run_migrations()
