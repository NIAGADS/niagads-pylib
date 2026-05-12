from datetime import datetime
from niagads.database.decorators import CompressedJson
from niagads.database.genomicsdb.schema.variant.base import VariantTableBase

from niagads.database.genomicsdb.schema.variant.types import RefSNPMergeHistory
from niagads.database.helpers import datetime_column
from sqlalchemy import INTEGER, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


# to do index? hash? on refsnp_id
class RefSNPAlias(VariantTableBase):
    __tablename__ = "refsnpalias"
    __table_args__ = (
        Index(
            "ix_refsnpalias_ref_snp_id",
            "ref_snp_id",
            postgresql_include=["merged_into", "merge_build"],
        ),
        VariantTableBase.__table_args__,
    )
    _stable_id = None

    ref_snp_alias_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_database_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reference.externaldatabase.external_database_id"),
        nullable=False,
    )
    ref_snp_id: Mapped[str] = mapped_column(String(25), nullable=False)
    merge_history: Mapped[list[RefSNPMergeHistory]] = mapped_column(
        CompressedJson, index=False, nullable=True
    )
    merged_into: Mapped[str] = mapped_column(String(25), index=False, nullable=False)
    merge_build: Mapped[int] = mapped_column(INTEGER, index=False, nullable=False)
    merge_date: Mapped[datetime] = datetime_column(nullable=False, index=False)
