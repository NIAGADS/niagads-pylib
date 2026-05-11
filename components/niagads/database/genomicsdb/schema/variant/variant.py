from typing import Optional

from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.types import LDPartner, VariantClass
from niagads.database.decorators import CompressedJson
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from niagads.database.genomicsdb.schema.variant.base import VariantTableBase

from niagads.database.helpers import enum_column
from niagads.database.mixins.embeddings import EmbeddingMixin
from niagads.database.mixins.ranges import GenomicRegionMixin

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class Variant(VariantTableBase, IdAliasMixin, GenomicRegionMixin, EmbeddingMixin):

    __tablename__ = "variant"
    __table_args__ = {
        **VariantTableBase.__table_args__,
        "info": {  # not really a view but we don't want alembic to create this table b/c it is partitioned
            "is_view": True
        },
    }

    variant_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_database_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reference.externaldatabase.external_database_id"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(nullable=False)
    ref_allele: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alt_allele: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    length: Mapped[int] = mapped_column(nullable=False)

    niagads_id: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_positional_id: Mapped[str] = mapped_column(Text, nullable=True)
    ref_snp_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    ga4gh_vrs: Mapped[Allele] = mapped_column(JSONB(none_as_null=True))
    hgvs: Mapped[Optional[str]] = mapped_column(nullable=True)

    variant_class: Mapped[VariantClass] = enum_column(
        VariantClass, native_enum=True, use_enum_names=True
    )
    is_adsp_variant: Mapped[Optional[bool]] = mapped_column(nullable=True)
    is_structural_variant: Mapped[Optional[bool]] = mapped_column(nullable=True)
    is_annotated: Mapped[Optional[bool]] = mapped_column(nullable=True)

    adsp_annotation: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True))
    most_severe_consequence: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True)
    )
    functional_annotation: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True)
    )
    allele_frequency: Mapped[Optional[dict]] = mapped_column(nullable=True)

    ld_partners: Mapped[Optional[list[LDPartner]]] = mapped_column(
        CompressedJson, nullable=True
    )

    functional_annotation_summary: Mapped[Optional[dict]] = mapped_column(nullable=True)
