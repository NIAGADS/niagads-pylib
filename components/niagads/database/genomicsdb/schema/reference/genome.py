from typing import List, Optional
from niagads.database.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.database.helpers import enum_column, enum_constraint
from niagads.genome_reference.human import GenomeBuild
from sqlalchemy import ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column


class GenomeReference(ReferenceTableBase):
    __tablename__ = "genomereference"
    _stable_id = "chromosome"
    __table_args__ = (
        enum_constraint("genome_build", GenomeBuild),
        ReferenceTableBase.__table_args__,
    )

    genome_reference_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    genome_build: Mapped[str] = enum_column(GenomeBuild)
    aliases: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    chromosome_length: Mapped[int] = mapped_column(nullable=False)
