from enum import Enum

# note the schema base is imported from core, not base so that all tables are generated
from niagads.database.genomicsdb.schemas.dataset.core import DatasetSchemaBase
from niagads.database.genomicsdb.schemas.core.core import CoreSchemaBase
from niagads.database.genomicsdb.schemas.gene.base import GeneSchemaBase


class Schema(Enum):
    DATABASE = DatasetSchemaBase
    CORE = CoreSchemaBase
    GENE = GeneSchemaBase

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
