from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import list_to_string
from sqlalchemy import CheckConstraint, Column, Enum


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


def enum_column(enum, nullable=False, index=True, native_enum=False):
    """
    Returns a SQLAlchemy Column for the given enum.

    Args:
        enum: The Enum class to use for the column.
        nullable (bool): Whether the column is nullable.
        index (bool): Whether to create an index on the column.

    Returns:
        Column: The SQLAlchemy column definition.
    """
    return Column(Enum(enum, native_enum=native_enum), nullable=nullable, index=index)
