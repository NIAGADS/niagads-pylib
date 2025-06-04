from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class ModelDumpMixin(object):
    def model_dump(self):
        """usage: track.model_dump()"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


class MetadataSchemaBase(DeclarativeBase):
    """base class for the metadata database models"""

    metadata = MetaData(schema="metadata")
