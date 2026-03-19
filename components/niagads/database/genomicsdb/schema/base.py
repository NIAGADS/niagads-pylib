import importlib
import pkgutil
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class GenomicsDBSchemaBase(DeclarativeBase):
    metadata = MetaData()

    @classmethod
    def get_schema(table_args):
        for arg in table_args:
            if isinstance(arg, dict) and "schema" in arg:
                return arg["schema"]
        raise ValueError("`schema` not found in the __table_args__")

    @classmethod
    def get_all_schemas(cls) -> list[str]:
        """Dynamically extract all schemas from GenomicsDBSchemaBase registry.

        Returns:
            list[str]: Unique list of schema names registered in the base.

        Source: AI-generated, see https://github.com/NIAGADS/niagads-pylib
        """
        schemas = []
        for mapper in cls.registry.mappers:
            table = mapper.class_.__table__
            if hasattr(table, "schema") and table.schema:
                schemas.append(table.schema)
        return list(set(schemas))

    @classmethod
    def is_valid_schema(cls, schema: str) -> bool:
        """Check if a schema string is a valid schema in GenomicsDBSchemaBase."""
        valid_schemas = cls.get_all_schemas()
        if schema.lower() in valid_schemas:
            return True
        else:
            raise ValueError(f"Schema {schema} is invalid for the GenomicsDB")

    @classmethod
    def register_table_classes(cls, package_root="niagads.database.genomicsdb.schema"):
        package = importlib.import_module(package_root)
        for _, modname, ispkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            if not ispkg and modname.endswith(".core"):
                importlib.import_module(modname)
