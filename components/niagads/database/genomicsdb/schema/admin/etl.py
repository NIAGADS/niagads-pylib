"""
Defines SQLAlchemy ORM models for ETL operation logging and run metadata.

These models support auditing, monitoring, and debugging of ETL processes in the admin schema.
"""

from datetime import datetime
from enum import auto
from typing import Optional

from niagads.common.types import ETLOperation, ProcessStatus
from niagads.database.genomicsdb.schema.admin.base import AdminTableBase
from niagads.database.genomicsdb.schema.admin.helpers import etlrun_fk_column
from niagads.database.helpers import datetime_column, enum_column, enum_constraint
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


# not using Admin
class ETLRun(AdminTableBase):
    __tablename__ = "etlrun"
    __table_args__ = (
        enum_constraint("status", ProcessStatus),
        enum_constraint("operation", ETLOperation),
        AdminTableBase.__table_args__,
    )
    etl_run_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    plugin_name: Mapped[str] = mapped_column(String(150), nullable=False)
    plugin_version: Mapped[str] = mapped_column(String(50), nullable=True)
    params: Mapped[dict] = mapped_column(JSONB)  # structured config/args
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # free-text errors/info
    status: Mapped[str] = enum_column(ProcessStatus, nullable=False)
    operation: Mapped[str] = enum_column(ETLOperation, nullable=False)
    is_test_run: Mapped[bool] = mapped_column(default=False)  # python default only

    # Timing + metrics
    start_time: Mapped[datetime] = datetime_column()
    end_time: Mapped[datetime] = datetime_column(nullable=True)
    rows_processed: Mapped[int] = mapped_column(server_default="0")
    run_id: Mapped[int] = etlrun_fk_column(nullable=True)
