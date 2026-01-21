"""
Defines SQLAlchemy ORM models for ETL operation logging and run metadata.

These models support auditing, monitoring, and debugging of ETL processes in the admin schema.
"""

from datetime import datetime
from enum import auto

from niagads.database import enum_column, enum_constraint
from niagads.database.mixins.columns import datetime_column
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomicsdb.schema.admin.base import AdminSchema
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


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


class ETLRun(AdminSchema):
    __tablename__ = "etlrun"
    __table_args__ = (
        enum_constraint("status", ProcessStatus),
        enum_constraint("operation", ETLOperation),
    )
    etl_run_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    plugin_name: Mapped[str] = mapped_column(String(150), nullable=False)
    plugin_version: Mapped[str] = mapped_column(String(50), nullable=True)
    params: Mapped[dict] = mapped_column(JSONB)  # structured config/args
    message: Mapped[str] = mapped_column(Text)  # free-text errors/info
    status: Mapped[str] = enum_column(ProcessStatus, nullable=False)
    operation: Mapped[str] = enum_column(ETLOperation, nullable=False)

    # Timing + metrics
    start_time: Mapped[datetime] = datetime_column()
    end_time: Mapped[datetime] = datetime_column(nullable=True)
    rows_processed: Mapped[int] = mapped_column(server_default=0)
