from datetime import datetime
from niagads.database.genomicsdb.schema.variant.base import VariantTableBase

from niagads.database.helpers import datetime_column
from sqlalchemy import INTEGER, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class RefSnpAlias(VariantTableBase):
    __tablename__ = "ref_snp_alias"
    __table_args__ = (VariantTableBase.__table_args__,)

    ref_snp_alias_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_database_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reference.externaldatabase.external_database_id"),
        nullable=False,
    )
    ref_snp_id: Mapped[str] = mapped_column(String(25), index=True, nullable=False)
    merged_into: Mapped[str] = mapped_column(String(25), index=True, nullable=False)
    merge_build: Mapped[int] = mapped_column(INTEGER, nullable=False)
    merge_date: Mapped[datetime] = datetime_column()
