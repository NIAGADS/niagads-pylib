from typing import Any, List

from alembic import context
from helpers.config import Settings
from niagads.common.core import ComponentBaseMixin
from sqlalchemy import Connection
from niagads.database.genomicsdb.schema.core import GenomicsDBSchemaBase


# can't get logging to wrok. alembic_wrapper will capture stdout and print
class MigrationRunner(ComponentBaseMixin):
    def __init__(self):
        super().__init__(debug=True)
        xArgs: dict = context.get_x_argument(as_dictionary=True)
        schema: str = xArgs.get("schema", None)
        self.__skip_fks = "skipForeignKeys" in xArgs
        self.__schema_independent: bool = True if schema is None else False

        self.__target_schemas: List[str] = (
            None
            if self.__schema_independent
            else (
                GenomicsDBSchemaBase.get_all_schemas()
                if schema.lower() == "all"
                else (
                    [schema.lower()]
                    if GenomicsDBSchemaBase.is_valid_schema(schema)
                    else None
                )
            )
        )

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

        if type_ == "table" and getattr(object_, "info", {}).get("is_view", False):
            return False

        # Filter by target schema if not schema-independent
        if not self.__schema_independent and hasattr(object_, "schema"):
            if object_.schema not in self.__target_schemas:
                return False

        return True

    def run_migrations_offline(self) -> None:
        config_kwargs = {
            "url": Settings.from_env().DATABASE_URI,
            "target_metadata": GenomicsDBSchemaBase.metadata,
            "literal_binds": True,
            "dialect_opts": {"paramstyle": "named"},
            "include_schemas": True,
            "include_object": self.include_object,
        }

        context.configure(**config_kwargs)
        with context.begin_transaction():
            context.run_migrations()

    def do_run_migrations(self, connection: Connection) -> None:

        config_kwargs = {
            "connection": connection,
            "target_metadata": GenomicsDBSchemaBase.metadata,
            "include_schemas": True,
            "include_object": self.include_object,
        }

        context.configure(**config_kwargs)
        with context.begin_transaction():
            context.run_migrations()
