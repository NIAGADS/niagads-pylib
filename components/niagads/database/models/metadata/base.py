from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class MetadataSchemaBase(DeclarativeBase):
    """base class for the metadata database models"""

    metadata = MetaData(schema="metadata")
