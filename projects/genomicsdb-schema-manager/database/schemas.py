from enum import Enum

# note the schema base is imported from core, not base so that all tables are generated
from niagads.database.models.metadata.core import MetadataSchemaBase
from niagads.database.models.index.core import IndexSchemaBase


class Schema(Enum):
    METADATA = MetadataSchemaBase
    INDEX = IndexSchemaBase

    @classmethod
    def _missing_(cls, value: str):
        if value is None:
            raise ValueError(
                "Schema value cannot be None; please run alembic with x argument: alembic -x schema=<schema_name>"
            )
        try:
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
        except ValueError as err:
            raise err

    @classmethod
    def base(cls, schema: str):
        return cls(schema).value
