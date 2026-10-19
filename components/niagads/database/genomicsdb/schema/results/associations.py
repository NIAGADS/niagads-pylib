from typing import Optional, Union

from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.mixins import BulkRecordRetrievalMixin
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.database.genomicsdb.schema.results.base import ResultsTableBase
from niagads.database.mixins.ranges import GenomicRegionMixin
from sqlalchemy import (
    JSON,
    TEXT,
    Integer,
    String,
    and_,
    func,
    literal_column,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
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
    async def _retrieve_associations_by_track(
        cls, session: AsyncSession, track_id: int
    ) -> dict[int, list[dict]]:
        """Retrieve associations for a data track.

        Args:
            session (AsyncSession): Active asynchronous database session.
            track_id (int): Database identifier for the data track.

        Returns:
            Mapping from the track identifier to matching association records.
        """

        track_ids = [track_id]
        sql_value_fields = cls._build_sql_value_field(track_ids, Integer)

        track_select = cls._build_lookup_select(
            sql_value_fields,
            lookup_field=cls.track_id,
            join_clause=[
                (cls, cls.track_id == sql_value_fields.c.lookup_value),
                (Track, Track.track_id == cls.track_id),
            ],
        )
        track_select = track_select.with_only_columns(
            sql_value_fields.c.lookup_value,
            track_select.selected_columns.record.op("||")(
                func.jsonb_build_object(
                    "track_stable_id",
                    Track.source_id,
                    "position",
                    func.lower(cls.span),
                )
            ).label("record"),
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
    async def _retrieve_associations_by_span(
        cls, session: AsyncSession, span: OneBasedGenomicRegion
    ) -> dict[str, list[dict]]:
        """Retrieve associations overlapping a genomic span.

        Args:
            session (AsyncSession): Active asynchronous database session.
            span (OneBasedGenomicRegion): One-based genomic region used to
                constrain the search.

        Returns:
            Mapping from the span string to matching association records.
        """
        bin_index = await IntervalBin.find_bin_index(
            session, span.chromosome, span.range
        )
        parent_bin = literal_column(f"'{bin_index}'::ltree")

        stmt = (
            select(
                func.row_to_json(cls.__table__.table_valued())
                .cast(JSONB)
                .label("record")
            )
            .select_from(cls)
            .join(Track, Track.track_id == cls.track_id)
            .where(
                and_(
                    cls.chromosome == str(span.chromosome),
                    parent_bin.op("@>")(cls.bin_index),
                    cls.span.op("&&")(span.range),
                )
            )
        )
        stmt = stmt.with_only_columns(
            stmt.selected_columns.record.op("||")(
                func.jsonb_build_object(
                    "track_stable_id",
                    Track.source_id,
                    "position",
                    func.lower(cls.span),
                )
            ).label("record"),
        )

        span_key = str(span)
        mappings = {span_key: []}
        # single column retrieved no mappings
        for record in (await session.execute(stmt)).scalars():
            mappings[span_key].append(record)

        return mappings

    @classmethod
    async def _retrieve_associations_by_variant(
        cls, session: AsyncSession, variant_id: str
    ) -> dict[str, list[dict]]:
        """Retrieve associations for a variant identifier.

        The identifier is matched exactly against either the variant stable ID
        or the numeric variant ID.

        Args:
            session (AsyncSession): Active asynchronous database session.
            variant_id (str): Stable or numeric variant identifier.

        Returns:
            Mapping from the variant identifier to matching association records.
        """
        variant_ids = [variant_id]
        sql_value_fields = cls._build_sql_value_field(variant_ids)

        variant_select = cls._build_lookup_select(
            sql_value_fields,
            lookup_field=cls.variant_stable_id,
            where_clause=or_(
                cls.variant_stable_id == sql_value_fields.c.lookup_value,
                cls.variant_id == sql_value_fields.c.lookup_value.cast(Integer),
            ),
            join_clause=[
                (cls, true()),
                (Track, Track.track_id == cls.track_id),
            ],
        )
        variant_select = variant_select.with_only_columns(
            sql_value_fields.c.lookup_value,
            variant_select.selected_columns.record.op("||")(
                func.jsonb_build_object(
                    "track_stable_id",
                    Track.source_id,
                    "position",
                    func.lower(cls.span),
                )
            ).label("record"),
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
        cls, session, lookup_value: Union[int, str, OneBasedGenomicRegion]
    ):
        """Find records that match an track database primary key (lookup_value:int), variant
        stable id (str), region (OneBasedGenomicRegion)

        Args:
            session (AsyncSession): Active asynchronous database session.
            lookup_value (int, str, OneBasedGenomicRegion): track_pk (int); variant
            stable id (str), region
        Returns:
            RecordRetrievalResult: Matching search result records grouped by
                identifier.
        """
        if isinstance(lookup_value, str):  # variant id
            return await cls._retrieve_associations_by_variant(session, lookup_value)
        elif isinstance(lookup_value, int):  # track record primary key
            return await cls._retrieve_associations_by_track(session, lookup_value)
        else:  # region
            return await cls._retrieve_associations_by_span(session, lookup_value)


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
