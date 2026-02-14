from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column


def etlrun_fk_column(nullable: bool = False, index: bool = True) -> Mapped[int]:
    """
    Create a mapped_column for an etl_run_id foreign key to admin.etlrun.etl_run_id.

    Args:
        nullable (bool): Whether the column is nullable. Defaults to False.
        index (bool): Whether to add an index. Defaults to True.

    Returns:
        Mapped[int]: SQLAlchemy mapped_column for etl_run_id foreign key to admin.etlrun.etl_run_id.

    Example:
        etl_run_id: Mapped[int] = run_id_fk_column()
    """
    return mapped_column(
        Integer, ForeignKey("admin.etlrun.etl_run_id"), nullable=nullable, index=index
    )
