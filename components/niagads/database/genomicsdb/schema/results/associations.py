from typing import Optional

from niagads.database.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.database.genomicsdb.schema.results.base import ResultsTableBase
from niagads.database.mixins.ranges import GenomicRegionMixin
from sqlalchemy import JSON, TEXT, String
from sqlalchemy.orm import Mapped, mapped_column


# GenomicRegionMixin can't just be added to base b/c of how indexes are generated
class VariantAssociation(ResultsTableBase, GenomicRegionMixin):
    __tablename__ = "variantassociation"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(ResultsTableBase._schema, __tablename__),
        *GenomicRegionMixin.set_bin_index_fk(ResultsTableBase._schema, __tablename__),
        ResultsTableBase.__table_args__,
    )

    variant_association_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    track_id: Mapped[int] = track_fk_column()
    variant_id: Mapped[int] = mapped_column(
        index=True
    )  # database primary key, but not FK b/c of variant table size
    variant_stable_id: Mapped[str] = mapped_column(
        index=True
    )  # `niagasds_id #FIXME:  change to variant_stable_id in variant tables
    neg_log10_pvalue: Mapped[float] = mapped_column(index=True)
    pvalue: Mapped[str] = mapped_column(String(25))
    effect_direction: Mapped[str] = mapped_column(String(2))
    # FIXME -> I don't think it needs to be a text field b/c optional now b/c of long INDEL handling
    test_allele: Mapped[Optional[str]] = mapped_column(TEXT)


class VariantTraitAssociation(
    ResultsTableBase, ExternalDatabaseMixin, GenomicRegionMixin
):
    __tablename__ = "varianttraitassociation"
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(ResultsTableBase._schema, __tablename__),
        *GenomicRegionMixin.set_bin_index_fk(ResultsTableBase._schema, __tablename__),
        ResultsTableBase.__table_args__,
    )

    variant_trait_association_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    variant_stable_id: Mapped[str] = mapped_column(
        index=True
    )  # `niagasds_id #FIXME:  change to variant_stable_id in variant tables
    neg_log10_pvalue: Mapped[float] = mapped_column(index=True)

    neg_log10_pvalue: Mapped[float] = mapped_column(index=True)
    pvalue: Mapped[str] = mapped_column(String(25))
    locus: Mapped[str] = mapped_column(TEXT)
    test_allele: Mapped[Optional[str]] = mapped_column(String(350))
    trait: Mapped[int] = ontology_term_fk_column()
    qualifiers: Mapped[Optional[dict]] = mapped_column(JSON(none_as_null=True))
