from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class CoreSchemaBase(DeclarativeBase):
    """Base class for the `Core` database models.

    This class serves as the base for all database models in the `core` schema.
    """

    metadata = MetaData(schema="core")
