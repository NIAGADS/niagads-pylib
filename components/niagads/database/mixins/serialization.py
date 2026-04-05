from datetime import datetime

from sqlalchemy import Date, DateTime
from sqlalchemy.dialects.postgresql import JSON, JSONB, ARRAY
from sqlalchemy_utils import LtreeType
from sqlalchemy_utils.types.ltree import Ltree


COMPLEX_TYPES = (ARRAY, LtreeType, JSONB, JSON, Date, DateTime)


class ModelDumpMixin(object):
    """
    Mixin providing a method to dump model column-value pairs as a dictionary.
    Mirrors pydantic model_dump
    """

    def __format_value(self, column_name):
        value = getattr(self, column_name)
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, Ltree):
            return str(value)
        return value

    def model_dump(self):
        """Return a dictionary of column names and their values for the model instance."""
        return {
            column.name: self.__format_value(column.name)
            for column in self.__table__.columns
        }
