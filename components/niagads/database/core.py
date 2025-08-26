from datetime import datetime

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import list_to_string
from sqlalchemy import CheckConstraint, Index, func, DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.types import String


class HousekeepingMixin(object):
    """
    Mixin providing common housekeeping fields for database models:
    - job_id: Foreign key to Core.Job table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    job_id: Mapped[int] = mapped_column(
        ForeignKey("core.job.job_id"), nullable=True, index=True, nullable=False
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
