"""`ETLLog` database model"""

from enum import auto

from niagads.database.common.utils import enum_column, enum_constraint
from niagads.database.genomicsdb.schemas.core.base import CoreSchemaBase
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


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
    script: Mapped[str] = mapped_column(String(150), nullable=False)
    args: Mapped[str] = mapped_column(Text)
    comment: Mapped[str] = mapped_column(Text)
    status: str = enum_column(ProcessStatus, nullable=False, index=False)
    operation: str = enum_column(ETLOperation, nullable=False, index=False)
