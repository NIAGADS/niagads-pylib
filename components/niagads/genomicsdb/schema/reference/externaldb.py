"""`ExternalDB` database model"""

from datetime import datetime
from niagads.database.mixins.columns import datetime_column
from niagads.genomicsdb.schema.reference.base import ReferenceSchemaBase
from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class ExternalDatabase(ReferenceSchemaBase):
    __tablename__ = "externaldatabase"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_externaldatabase_name_version"),
    )
    external_database_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(300), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=True)
    download_url: Mapped[str] = mapped_column(String(300), nullable=True)
    download_date: Mapped[datetime] = datetime_column(nullable=True)
