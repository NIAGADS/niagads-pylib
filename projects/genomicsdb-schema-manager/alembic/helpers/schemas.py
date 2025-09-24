from enum import Enum

# note the schema base is imported from `core`, which contains both the base and the models
# not `base`, which just defines the base; this ensures all tables are generated
# see https://stackoverflow.com/a/77767002
from niagads.genomicsdb.models.admin.core import AdminSchemaBase
from niagads.genomicsdb.models.reference.core import ReferenceSchemaBase
from niagads.genomicsdb.models.dataset.core import DatasetSchemaBase
from niagads.genomicsdb.models.gene.core import GeneSchemaBase
from niagads.genomicsdb.models.variant.core import VariantSchemaBase

from niagads.settings.core import CustomSettings


class Settings(CustomSettings):
    DATABASE_URI: str


class Schema(Enum):
    ADMIN = AdminSchemaBase
    REFERENCE = ReferenceSchemaBase
    DATASET = DatasetSchemaBase
    VARIANT = VariantSchemaBase
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
