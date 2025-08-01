from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class DatasetSchemaBase(DeclarativeBase):
    """base class for the `Metadata` database models"""

    metadata = MetaData(schema="dataset")
