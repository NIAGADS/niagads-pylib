from datetime import datetime

from sqlalchemy import DATETIME, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey


class HousekeepingMixin(object):
    """
    Mixin providing common housekeeping fields for database models:
    - etl_log_id: Foreign key to Core.ETLLog table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    etl_log_id: Mapped[int] = mapped_column(
        ForeignKey("core.etllog.etl_log_id"), nullable=False, index=True
    )
    modification_date: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=False,
    )
    # is_private: Mapped[bool] = mapped_column(nullable=True, index=True)
