from datetime import datetime

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import list_to_string
from sqlalchemy import DATETIME, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy import MetaData


class HousekeepingMixin(object):
    """
    Mixin providing common housekeeping fields for database models:
    - job_id: Foreign key to Core.Job table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    job_id: Mapped[int] = mapped_column(
        ForeignKey("core.job.job_id"), nullable=True, index=True
    )
    modification_date: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=False,
    )
    is_private: Mapped[bool] = mapped_column(nullable=True, index=True)


class ModelDumpMixin(object):
    """
    Mixin providing a method to dump model columns as a dictionary.
    """

    def model_dump(self):
        """Return a dictionary of column names and their values for the model instance."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


def enum_constraint(field_name: str, enum: CaseInsensitiveEnum):
    """
    Returns a SQLAlchemy CheckConstraint that restricts a field to values in the given enum.

    Args:
        field_name (str): The name of the field to constrain.
        enum (CaseInsensitiveEnum): The enum containing allowed values.

    Returns:
        CheckConstraint: The constraint for the field.
    """
    return CheckConstraint(
        f"{field_name} in ({list_to_string(enum.list(), quote=True, delim=', ')})",
        name=f"check_{field_name}",
    )


class DeclarativeModelBaseFactory:
    """
    Factory for creating SQLAlchemy DeclarativeBase classes with optional schema and mixins.
    """

    @staticmethod
    def create(schema: str = None, housekeeping: bool = True):
        """
        Create a DeclarativeBase class with optional schema and mixins.

        Args:
            schema (str, optional): The database schema to use.
            housekeeping (bool): Whether to include HousekeepingMixin.

        Returns:
            DeclarativeBase: A new DeclarativeBase subclass.
        """
        bases = (ModelDumpMixin,)
        if housekeeping:
            bases = (HousekeepingMixin,) + bases
        bases = bases + (DeclarativeBase,)

        class Base(*bases):
            if schema:
                metadata = MetaData(schema=schema)
            else:
                metadata = MetaData()

        return Base
