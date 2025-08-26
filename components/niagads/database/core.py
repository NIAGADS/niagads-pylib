from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import list_to_string
from sqlalchemy import CheckConstraint


class ModelDumpMixin(object):
    def model_dump(self):
        """usage: track.model_dump()"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


def enum_constraint(field_name: str, enum: CaseInsensitiveEnum):
    """
    Returns a SQLAlchemy CheckConstraint that restricts a field to values in the given enum.
    """
    return CheckConstraint(
        f"{field_name} in ({list_to_string(enum.list(), quote=True, delim=', ')})",
        name=f"check_{field_name}",
    )
