from niagads.database.decorators import AutoDateTime
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import list_to_string
from sqlalchemy import CheckConstraint, Column, Enum, func
from sqlalchemy.orm import mapped_column


def datetime_column(nullable: bool = False):
    """
    Returns a SQLAlchemy mapped_column for TIMESTAMP with server_default=func.now().

    Args:
        nullable (bool): Whether the column should be nullable. Default is False.

    Returns:
        sqlalchemy.orm.MappedColumn: Configured mapped_column instance.
    """
    return mapped_column(
        AutoDateTime,
        server_default=None if nullable else func.now(),
        nullable=nullable,
    )


def enum_constraint(
    field_name: str, enum: CaseInsensitiveEnum, use_enum_names: bool = False
):
    """
    Returns a SQLAlchemy CheckConstraint that restricts a field to values in the given enum.

    Args:
        field_name (str): The name of the field to constrain.
        enum (CaseInsensitiveEnum): The enum containing allowed values.

    Returns:
        CheckConstraint: The constraint for the field.
    """
    if not isinstance(enum, (list, tuple)):
        enum = [enum]  # this way we can handle the use_enum_names flag only once

    allowed_values = []
    enum_cls: CaseInsensitiveEnum
    for enum_cls in enum:
        allowed_values.extend(enum_cls.list(return_enum_names=use_enum_names))

    return CheckConstraint(
        f"{field_name} in ({list_to_string(allowed_values, quote=True, delim=', ')})",
        name=f"check_{field_name}",
    )


def enum_column(
    enum: CaseInsensitiveEnum,
    nullable=False,
    index=True,
    native_enum=False,
    use_enum_names: bool = False,
):
    """
    Returns a SQLAlchemy Column for the given enum.

    Args:
        enum: The Enum class to use for the column, or a list/tuple of Enum
            classes. If multiple enums are provided, their values are combined
            into a single SQLAlchemy Enum.
        nullable (bool): Whether the column is nullable.
        index (bool): Whether to create an index on the column.

    Returns:
        Column: The SQLAlchemy column definition.
    """
    if not isinstance(enum, (list, tuple)):
        enum = [enum]  # this way we can handle the use_enum_names flag only once

    combined_values = []
    enum_cls: CaseInsensitiveEnum
    for enum_cls in enum:
        combined_values.extend(enum_cls.list(return_enum_names=use_enum_names))
    name = "_".join(cls.__name__ for cls in enum)

    sa_enum = Enum(*combined_values, native_enum=native_enum, name=name.lower())

    return Column(sa_enum, nullable=nullable, index=index)
