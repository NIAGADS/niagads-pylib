from typing import Optional

from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.database.genomicsdb.schema.mixins import BulkRecordRetrievalMixin
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.database.genomicsdb.schema.results.base import ResultsTableBase
from niagads.database.mixins.ranges import GenomicRegionMixin
from sqlalchemy import JSON, TEXT, Integer, String, or_
from sqlalchemy.orm import Mapped, mapped_column


# GenomicRegionMixin can't just be added to base b/c of how indexes are generated
class VariantAssociation(
    ResultsTableBase, GenomicRegionMixin, BulkRecordRetrievalMixin
):
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

    @classmethod
    async def _retrieve_associations_by_track(cls, session, track_id: int):
        """assume that track annotation -> track_id mapping is done in calling function,
        so we just need to lookup by primary key

        # TODO: evaluate whether this needs to be for multiple track_ids. not sure if
        # use case exists
        """

        track_ids = [track_id]
        sql_value_fields = cls._build_sql_value_field(track_ids, Integer)

        track_select = cls._build_lookup_select(
            sql_value_fields,
            lookup_field=cls.track_id,
        )

        # ie., a bit overkill but matching template in case
        # we decide to allow lookups on multiple tracks
        mappings = {identifier: [] for identifier in dict.fromkeys(track_ids)}
        for row in await cls._execute_lookup(
            session,
            sql_value_fields,
            track_select.subquery("track_matches"),
        ):
            record = row["record"]
            track_key = row["lookup_value"]

            if record is not None:
                mappings[track_key].append(record)

        return mappings

    @classmethod
    async def _retrieve_associations_by_variant(cls, session, variant_id: str):
        variant_ids = [variant_id]
        sql_value_fields = cls._build_sql_value_field(variant_ids)

        variant_select = cls._build_lookup_select(
            sql_value_fields,
            lookup_field=cls.variant_stable_id,
            where_clause=or_(
                cls.variant_stable_id == sql_value_fields.c.lookup_value,
                cls.variant_id == sql_value_fields.c.lookup_value.cast(Integer),
            ),
        )

        mappings = {identifier: [] for identifier in dict.fromkeys(variant_ids)}
        for row in await cls._execute_lookup(
            session,
            sql_value_fields,
            variant_select.subquery("variant_matches"),
        ):
            record = row["record"]
            variant_key = row["lookup_value"]

            if record is not None:
                mappings[variant_key].append(record)

        return mappings

    @classmethod
    async def retrieve_records(
        cls,
        session,
        *,
        track_id: int = None,
        variant_id: str = None,
        span: OneBasedGenomicRegion = None,
    ):
        if track_id:
            return await cls._retrieve_associations_by_track(session, track_id)

        elif variant_id:
            return await cls._retrieve_associations_by_variant(session, variant_id)

        elif span is not None:
            return await cls._retrieve_associations_by_span(session, span)


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
