from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class IndexSchemaBase(DeclarativeBase):
    """base class for the `Index` database models"""

    metadata = MetaData(schema="index")
