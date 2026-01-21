from sqlalchemy import DATETIME, func
from sqlalchemy.orm import mapped_column


def datetime_column(nullable: bool = False):
    """
    Returns a SQLAlchemy mapped_column for DATETIME with server_default=func.now().

    Args:
        nullable (bool): Whether the column should be nullable. Default is False.

    Returns:
        sqlalchemy.orm.MappedColumn: Configured mapped_column instance.
    """
    return mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=nullable,
    )
