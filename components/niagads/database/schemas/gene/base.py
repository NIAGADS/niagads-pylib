from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class GeneSchemaBase(DeclarativeBase):
    """base class for the `Gene` database models"""

    metadata = MetaData(schema="gene")
