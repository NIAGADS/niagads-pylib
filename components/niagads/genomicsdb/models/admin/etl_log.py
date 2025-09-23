"""`ETLLog` database model"""

from datetime import datetime
from enum import auto

from niagads.database import enum_column, enum_constraint
from niagads.genomicsdb.models.admin.base import CoreSchemaBase
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class ETLOperation(CaseInsensitiveEnum):
    BULK_LOAD = auto()
    UPDATE = auto()
    DELETE = auto()
    PATCH = auto()
    INSERT = auto()


class ETLLog(CoreSchemaBase):
    __tablename__ = "etllog"
    __table_args__ = (
        enum_constraint("status", ProcessStatus),
        enum_constraint("operation", ETLOperation),
    )
    etl_log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Provenance / context
    plugin_name: Mapped[str] = mapped_column(String(150), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB)  # structured config/args
    message: Mapped[str] = mapped_column(Text)  # free-text errors/info

    # Status + operation
    status: str = enum_column(ProcessStatus, nullable=False)  # indexed by enum_column
    operation: str = enum_column(ETLOperation, nullable=False)  # indexed by enum_column

    # Run + version info
    run_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    code_version: Mapped[str] = mapped_column(String(50), nullable=True)
    repo: Mapped[str] = mapped_column(String(150), nullable=True)

    # Timing + metrics
    start_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    end_time: Mapped[datetime] = mapped_column(DateTime)
    rows_processed: Mapped[int] = mapped_column(default=0)
