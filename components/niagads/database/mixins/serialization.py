from datetime import datetime

from sqlalchemy import ARRAY, Date, DateTime
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy_utils import LtreeType


COMPLEX_TYPES = (ARRAY, LtreeType, JSONB, JSON, Date, DateTime)


class ModelDumpMixin(object):
    """
    Mixin providing a method to dump model column-value pairs as a dictionary.
    Mirrors pydantic model_dump
    """

    def model_dump(self):
        """Return a dictionary of column names and their values for the model instance."""
        return {
            column.name: (
                value.strftime("%Y-%m-%d")
                if isinstance((value := getattr(self, column.name)), datetime)
                else value
            )
            for column in self.__table__.columns
        }
