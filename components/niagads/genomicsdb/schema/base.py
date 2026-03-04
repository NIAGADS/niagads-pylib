from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class GenomicsDBSchemaBase(DeclarativeBase):
    metadata = MetaData()

    def get_schema(table_args):
        for arg in table_args:
            if isinstance(arg, dict) and "schema" in arg:
                return arg["schema"]
        raise ValueError("`schema` not found in the __table_args__")
