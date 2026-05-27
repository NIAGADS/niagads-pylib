"""`ExternalDB` database model"""

from datetime import datetime
from typing import Optional

from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.helpers import datetime_column
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from niagads.database.genomicsdb.schema.reference.base import ReferenceTableBase
from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class ExternalDatabase(ReferenceTableBase, IdAliasMixin):
    __tablename__ = "externaldatabase"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_externaldatabase_name_version"),
        ReferenceTableBase.__table_args__,
    )
    _stable_id = "database_key"
    external_database_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    database_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(300), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=True)
    download_url: Mapped[str] = mapped_column(String(300), nullable=True)
    download_date: Mapped[datetime] = datetime_column(nullable=True)
    release_date: Mapped[datetime] = datetime_column(nullable=True)
    database_type_id: Mapped[Optional[int]] = ontology_term_fk_column(
        nullable=True, index=True
    )
