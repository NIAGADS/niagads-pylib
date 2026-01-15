"""`ETLLog` database model"""

from datetime import datetime
from enum import auto

from niagads.database import enum_column, enum_constraint
from niagads.genomicsdb.schema.admin.base import AdminSchemaBase
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class ETLOperation(CaseInsensitiveEnum):
    """
    Type of ETL operation:
    - LOAD: Insert new or Update existing records.
    - UPDATE: Update existing records.
    - DELETE: Delete records.
    - PATCH: Partially update records.
    - INSERT: Insert new records.
    """

    INSERT = auto()
    UPDATE = auto()
    LOAD = auto()
    PATCH = auto()
    DELETE = auto()
    SKIP = auto()


class ETLTask(AdminSchemaBase):
    __tablename__ = "etltask"
    __table_args__ = (
        enum_constraint("status", ProcessStatus),
        enum_constraint("operation", ETLOperation),
    )
    task_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    plugin_name: Mapped[str] = mapped_column(String(150), nullable=False)
    code_version: Mapped[str] = mapped_column(String(50), nullable=True)
    params: Mapped[dict] = mapped_column(JSONB)  # structured config/args
    message: Mapped[str] = mapped_column(Text)  # free-text errors/info
    status: Mapped[str] = enum_column(ProcessStatus, nullable=False)
    operation: Mapped[str] = enum_column(ETLOperation, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # Timing + metrics
    start_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    end_time: Mapped[datetime] = mapped_column(DateTime, default=None, nullable=True)
    rows_processed: Mapped[int] = mapped_column(default=0)
