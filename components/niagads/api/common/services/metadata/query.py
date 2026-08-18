from enum import Enum, auto
from typing import Any, List, Optional

from fastapi import HTTPException
from niagads.api.common.constants import SHARD_PATTERN
from niagads.api.common.models.domain.parameters.filters.expression_filter import Triple
from niagads.api.common.models.domain.parameters.types import ResponseView
from niagads.api.common.models.service.request import RequestDataModel
from niagads.common.track.models import (
    ExperimentalDesign,
    Phenotype,
    Provenance,
)
from niagads.database.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.utils.list import list_to_string
from niagads.utils.string import regex_replace
from sqlalchemy import Column, Select, String, Values, column, distinct, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession


class TrackDatabase(Enum):
    FILER = auto()
    GENOMICSDB = auto()
    OPEN_ACCESS = auto()


class MetadataQueryService:
    def __init__(
        self,
        session: AsyncSession,
        request: RequestDataModel = None,
        track_database: TrackDatabase = TrackDatabase.OPEN_ACCESS,
    ):
        self.__database_session = session
        self.__request = request
        self.__track_database = track_database
        self.__track_filter = self.__set_filter(Track)
        self.__collection_filter = self.__set_filter(Collection)

    def __set_filter(self, model):
        """Generate database filter based on track database type.

        Args:
            model: SQLAlchemy model class (Track or Collection).

        Returns:
            BooleanClauseList filter expression or None for OPEN_ACCESS.
        """
        field = f"is_filer_{model.__name__.lower()}"
        column = getattr(model, field)
        if self.__track_database == TrackDatabase.FILER:
            return column.is_(True)
        if self.__track_database == TrackDatabase.GENOMICSDB:
            return (column.is_(False)) | (column.is_(None))

        return None

    def __apply_table_filter(self, stmt: Select, filter) -> Select:
        if filter is not None:
            return stmt.where(filter)
        return stmt

    def __apply_filter(self, stmt: Select, model) -> Select:
        # FIXME -> make filters a model -> value map
        if model is Track:
            return self.__apply_table_filter(stmt, self.__track_filter)
        elif model is Collection:
            return self.__apply_table_filter(stmt, self.__collection_filter)
        else:
            raise NotImplementedError("No filter handling implemented for this model")

    async def validate_tracks(self, tracks: List[str]):
        # solution for finding tracks not in the table adapted from
        # https://stackoverflow.com/a/73691503

        lookups = Values(Column("id", String), name="lookups").data(
            [(t,) for t in tracks]
        )

        stmt = (
            select(lookups.c.id)
            .outerjoin(Track, Track.source_id == lookups.c.id)
            .where(Track.source_id == None)
        )
        stmt = self.__apply_filter(stmt, Track)
        result = (await self.__database_session.execute(stmt)).all()

        if len(result) > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Invalid tracks found: `{list_to_string(result)}`.",
            )
        else:
            return True

    async def validate_collection(self, pk: str) -> int:
        """validate a collection by primary_key"""
        stmt = select(Collection).where(Collection.primary_key.ilike(pk))
        stmt = self.__apply_filter(stmt, Collection)
        try:
            collection = (await self.__database_session.execute(stmt)).scalar_one()
            return collection
        except NoResultFound as e:
            raise HTTPException(status_code=404, detail=f"Collection `{pk}` not found")

    async def get_track_count(self) -> int:
        statement = select(func.count(Track.source_id)).where(
            Track.data_store.in_(self.__data_store)
        )

        result = (await self.__database_session.execute(statement)).scalars().first()
        return result

    async def get_collection(self, collection_id: str = None) -> List[Collection]:
        stmt: Select = select(
            Collection.collection_key,
            Collection.name,
            Collection.description,
            func.count(TrackCollectionLink.track_collection_link_id).label(
                "num_tracks"
            ),
        ).join(
            TrackCollectionLink,
            TrackCollectionLink.collection_id == Collection.collection_id,
        )
        stmt = self.__apply_filter(stmt)

        if collection_id is not None:
            self.validate_collection(collection_id)
            stmt = stmt.where(Collection.source_id == collection_id)

        stmt = stmt.group_by(Collection).order_by(Collection.collection_id)
        result = (await self.__database_session.execute(stmt)).scalars().all()

        return result

    # FIXME: shard_root_id no longer exists
    def generate_sharded_track_metadata(self, t: Track):
        t.id = t.shard_root_id
        t.file_properties["url"] = regex_replace(
            SHARD_PATTERN, "$CHR", t.file_properties["url"]
        )

        # remove _chrN_ from fields
        t.name = regex_replace(f" {SHARD_PATTERN} ", " ", t.name)
        t.description = regex_replace(f" {SHARD_PATTERN} ", " ", t.description)

        # set individual file names to None
        t.raw_file_url = None
        t.file_name = None

        return t

    async def get_sharded_ids(self, rootShardTrackId: str):
        statement = (
            select(Track.source_id)
            .where(Track.shard_root_id == rootShardTrackId)
            .order_by(Track.source_id)
        )
        result = (await self.__database_session.execute(statement)).scalars().all()
        return result

    async def get_sharded_track_urls(self, rootShardTrackId: str):
        statement = (
            select(Track.url)
            .where(Track.shard_root_id == rootShardTrackId)
            .order_by(Track.source_id)
        )
        result = (await self.__database_session.execute(statement)).scalars().all()
        return result

    async def get_collection_track_metadata(
        self,
        collection_name: str,
        response_type=ResponseView.FULL,
    ) -> List[Track]:

        collection: Collection = await self.validate_collection(collection_name)

        # if sharded URLs need to be mapped through IDS to find all shards
        target = (
            self.__set_query_target(ResponseView.IDS)
            if response_type == ResponseView.URLS and collection.is_sharded_collection
            else self.__set_query_target(response_type)
        )

        stmt = (
            select(target)
            .join(TrackCollectionLink, TrackCollectionLink.id == Track.source_id)
            .where(TrackCollectionLink.collection_id == collection.collection_id)
            .order_by(Track.source_id)
        )

        stmt = self.__apply_filter(stmt, Collection)

        result = (await self.__database_session.execute(stmt)).scalars().all()

        # TODO: RESUME - HERE --> messaging -> class member w/accessor function so that it can
        # be accessed by parent endpoint service

        if response_type == ResponseView.COUNTS:
            return {"count": result[0]}

        if collection.is_sharded_collection:
            if response_type == ResponseView.IDS:
                # FIXME: I think this has changed
                self.__request
                self.__request.add_message(
                    "Data are split by chromosome into 22 files per track.  For every `track` in the collection, there are 22 track identifiers and metadata are linked to the `id` of the first shard (`chr1`)."
                )
                result = [await self.get_sharded_ids(t) for t in result]
                return sum(result, [])  # unnest nested list
            if response_type == ResponseView.URLS:
                self.__request.add_message(
                    "Data are split by chromosome into 22 files per track, differentiated by `_chrN_` in the file name."
                )
                result = [await self.get_sharded_track_urls(t) for t in result]
                return sum(result, [])

            # otherwise full or summary result
            self.__request.add_message(
                f"Track data are split by chromosome.  Summary metadata are linked to the `id` of the first shard (`chr1`)."
            )
            return [self.generate_sharded_track_metadata(t) for t in result]
        return result

    async def get_track_metadata(
        self, tracks: List[str], response_type=ResponseView.FULL, validate=True
    ) -> List[Track]:
        target = self.__set_query_target(response_type)
        statement = (
            select(target).where(Track.source_id.in_(tracks)).order_by(Track.source_id)
        )

        if validate:
            await self.validate_tracks(tracks)

        track_records: list[Track] = (
            (await self.__database_session.execute(statement)).scalars().all()
        )

        return track_records

    def __add_statement_filters(self, statement, filters: List[Triple]):
        column: Column = None
        for triple in filters:
            tmpT = None
            if triple.field == "biosample_type":
                column = Track.biosample_characteristics[triple.field].astext
            elif triple.field in Phenotype.model_fields:
                column = Track.participant_phenotypes[triple.field].astext
            elif triple.field in Provenance.model_fields:
                column = Track.provenance[triple.field].astext
            elif triple.field in ExperimentalDesign.model_fields:
                column = Track.experimental_design[triple.field].astext
            elif triple.field == "cell":
                biosample_filter = Triple(
                    field="biosample_type", operator="like", value="cell"
                )
                statement = self.__add_statement_filters(statement, [biosample_filter])
                # don't do like matches b/c wildcards are already present
                if triple.operator == "like":
                    operator = "eq"
                if triple.operator == "not like":
                    operator = "neq"
                else:
                    operator = triple.operator

                # if we don't do this, async overwrite of the value just keep
                # concantenating "term", etc
                tmpT = Triple(
                    value=f'%"term": "%{triple.value}%"%',
                    operator=operator,
                    field=triple.field,
                )
                column = Track.biosample_characteristics["biosample"].astext

            elif triple.field == "tissue":
                column = Track.biosample_characteristics["tissue"].astext

                # have to use wildcards b/c array
                if triple.operator == "eq":
                    operator = "like"
                if triple.operator == "neq":
                    operator = "not like"
                else:
                    operator = triple.operator

                tmpT = Triple(
                    value=triple.value,
                    operator=operator,
                    field=triple.field,
                )

            else:
                column = Track.__table__.c[triple.field]

            statement = statement.filter(
                triple.to_prepared_statement(column)
                if tmpT is None
                else tmpT.to_prepared_statement(column)
            )

        return statement

    @staticmethod
    def __set_query_target(response_type: ResponseView):
        match response_type:
            case ResponseView.IDS:
                return Track.source_id
            case ResponseView.COUNTS:
                return func.count(Track.source_id)
            case ResponseView.URLS:
                return Track.file_properties["url"]
            case _:
                return Track

    async def query_track_metadata(
        self,
        genome_build: str,
        filters: Optional[List[str]],
        keyword: Optional[str],
        response_type: ResponseView,
        limit: int = None,
        offset: int = None,
    ) -> List[Track]:

        target = self.__set_query_target(response_type)
        statement = (
            select(target)
            .filter(Track.genome_build == genome_build)
            .filter(Track.data_store.in_(self.__data_store))
        )

        if filters is not None:
            statement = self.__add_statement_filters(statement, filters)
        if keyword is not None:
            statement = statement.filter(
                Track.searchable_text.regexp_match(keyword, "i"),
            )

        if response_type != ResponseView.COUNTS:
            statement = statement.order_by(Track.source_id)

        if limit != None:
            statement = statement.limit(limit)

        if offset != None:
            statement = statement.offset(offset)

        result = await self.__database_session.execute(statement)

        if response_type == ResponseView.COUNTS:
            return {"count": result.scalars().one()}
        else:
            return result.scalars().all()

    async def get_track_filter_summary(
        self, filterField: str, inclCounts: Optional[bool] = False
    ) -> dict:

        modelField = filterField  # FIXME: TRACK_SEARCH_FILTER_FIELD_MAP[filterField]["model_field"]

        valueCol = column(getattr(Track, modelField))
        if "biosample" in modelField:
            valueCol = valueCol["tissue_category"].astext
        # statement = select(valueCol, Track.source_id).group_by(valueCol).count()
        statement = (
            select(distinct(valueCol), func.count(Track.source_id))
            .where(valueCol.is_not(None))
            .group_by(valueCol)
            if inclCounts
            else select(distinct(valueCol)).where(valueCol.is_not(None))
        )

        result = (await self.__database_session.execute(statement)).all()
        return (
            {row[0]: row[1] for row in result}
            if inclCounts
            else [value for value, in result]
        )

    async def get_genome_build(self, tracks: List[str], validate=True) -> str:
        """retrieves the genome build for a set of tracks; returns track -> genome build mapping if not all on same assembly"""

        if validate:
            await self.validate_tracks(tracks)

        statement = select(distinct(Track.genome_build)).where(
            Track.source_id.in_(tracks)
        )

        result = (await self.__database_session.execute(statement)).all()
        if len(result) > 1:
            statement = (
                select(Track.source_id, Track.genome_build)
                .where(Track.source_id.in_(tracks))
                .order_by(Track.genome_build, Track.source_id)
            )
            result = (await self.__database_session.execute(statement)).all()
            return {row[0]: row[1] for row in result}
        else:
            return result[0][0]
