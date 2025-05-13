from niagads.exceptions.core import ValidationError

from niagads.database.models.metadata.collection import Collection, TrackCollection
from niagads.database.models.metadata.track import Track
from niagads.database.models.metadata.composite_attributes import (
    ExperimentalDesign,
    Phenotype,
    Provenance,
    TrackDataStore,
)
from niagads.open_access_api_common.config.constants import SHARD_PATTERN
from niagads.open_access_api_common.models.response.request import RequestDataModel
from niagads.open_access_api_common.parameters.expression_filter import Triple
from niagads.open_access_api_common.parameters.response import ResponseContent
from niagads.utils.string import regex_replace
from sqlmodel import select, col, or_, func, distinct
from sqlalchemy import Column, Values, String, column as sqla_column
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from typing import List, Optional

from niagads.utils.list import list_to_string


class MetadataQueryService:
    def __init__(
        self,
        session: AsyncSession,
        request: RequestDataModel = None,
        dataStore: List[TrackDataStore] = [TrackDataStore.SHARED],
    ):
        self.__session = session
        self.__request = request
        self.__dataStore = dataStore

    async def validate_tracks(self, tracks: List[str]):
        # solution for finding tracks not in the table adapted from
        # https://stackoverflow.com/a/73691503
        lookups = Values(sqla_column("track_id", String), name="lookups").data(
            [(t,) for t in tracks]
        )
        statement = (
            select(lookups.c.track_id)
            .outerjoin(Track, col(Track.track_id) == lookups.c.track_id)
            .filter(col(Track.data_store).in_(self.__dataStore))
            .where(col(Track.track_id) == None)
        )

        result = (await self.__session.execute(statement)).all()
        if len(result) > 0:
            raise ValidationError(
                f"Invalid track identifiers found: {list_to_string(result)}"
            )
        else:
            return True

    async def validate_collection(self, name: str) -> int:
        """validate a collection by name"""
        statement = (
            select(Collection)
            .where(col(Collection.name).ilike(name))
            .filter(col(Collection.data_store).in_(self.__dataStore))
        )
        try:
            collection = (await self.__session.execute(statement)).scalar_one()
            return collection
        except NoResultFound as e:
            raise ValidationError(f"Invalid collection: {name}")

    async def get_track_count(self) -> int:
        statement = select(func.count(Track.track_id)).where(
            Track.data_store.in_(self.__dataStore)
        )

        result = (await self.__session.execute(statement)).scalars().first()
        return result

    async def get_collections(self) -> List[Collection]:
        statement = (
            select(
                Collection.name,
                Collection.description,
                func.count(TrackCollection.track_id).label("num_tracks"),
            )
            .join(
                TrackCollection,
                TrackCollection.collection_id == Collection.collection_id,
            )
            .filter(col(Collection.data_store).in_(self.__dataStore))
        )
        statement = statement.group_by(Collection).order_by(Collection.collection_id)
        result = (await self.__session.execute(statement)).mappings().all()
        return result

    def generate_sharded_track_metadata(self, t: Track):
        t.track_id = t.shard_root_track_id
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

    async def get_sharded_track_ids(self, rootShardTrackId: str):
        statement = (
            select(Track.track_id)
            .where(col(Track.shard_root_track_id) == rootShardTrackId)
            .order_by(Track.track_id)
        )
        result = (await self.__session.execute(statement)).scalars().all()
        return result

    async def get_sharded_track_urls(self, rootShardTrackId: str):
        statement = (
            select(Track.url)
            .where(col(Track.shard_root_track_id) == rootShardTrackId)
            .order_by(Track.track_id)
        )
        result = (await self.__session.execute(statement)).scalars().all()
        return result

    async def get_shard(self, track: str, chromosome: str):
        # statement = select(Track).where(col())
        pass

    async def get_collection_track_metadata(
        self, collectionName: str, track: str = None, responseType=ResponseContent.FULL
    ) -> List[Track]:
        collection: Collection = await self.validate_collection(collectionName)

        # if sharded URLs need to be mapped through IDS to find all shards
        target = (
            self.__set_query_target(ResponseContent.IDS)
            if responseType == ResponseContent.URLS and collection.tracks_are_sharded
            else self.__set_query_target(responseType)
        )

        statement = (
            select(target)
            .join(TrackCollection, TrackCollection.track_id == Track.track_id)
            .where(TrackCollection.collection_id == collection.collection_id)
            .filter(col(Track.data_store).in_(self.__dataStore))
        )

        if track is not None:
            statement = statement.where(col(Track.track_id) == track)

        result = (await self.__session.execute(statement)).scalars().all()
        if responseType == ResponseContent.COUNTS:
            return {"num_tracks": result[0]}
        if collection.tracks_are_sharded:
            if responseType == ResponseContent.IDS:
                self.__request.add_message(
                    "Data are split by chromosome into 22 files per track.  For every `track` in the collection, there are 22 track identifiers and metadata are linked to the `track_id` of the first shard (`chr1`)."
                )
                result = [await self.get_sharded_track_ids(t) for t in result]
                return sum(result, [])  # unnest nested list
            if responseType == ResponseContent.URLS:
                self.__request.add_message(
                    "Data are split by chromosome into 22 files per track, differentiated by `_chrN_` in the file name."
                )
                result = [await self.get_sharded_track_urls(t) for t in result]
                return sum(result, [])

            # otherwise full or summary result
            self.__request.add_message(
                f"Track data are split by chromosome.  Summary metadata are linked to the `track_id` of the first shard (`chr1`)."
            )
            return [self.generate_sharded_track_metadata(t) for t in result]
        return result

    async def get_track_metadata(
        self, tracks: List[str], responseType=ResponseContent.FULL, validate=True
    ) -> List[Track]:
        target = self.__set_query_target(responseType)
        statement = (
            select(target)
            .filter(col(Track.track_id).in_(tracks))
            .order_by(Track.track_id)
        )

        if validate:
            await self.validate_tracks(tracks)

        result = (await self.__session.execute(statement)).scalars().all()
        return result

    def __add_statement_filters(self, statement, filters: List[Triple]):
        column: Column = None
        for triple in filters:
            tmpT = None
            if triple.field == "biosample_type":
                column = Track.biosample_characteristics[triple.field].astext
            elif triple.field in Phenotype.model_fields:
                column = Track.subject_phenotypes[triple.field].astext
            elif triple.field in Provenance.model_fields:
                column = Track.provenance[triple.field].astext
            elif triple.field in ExperimentalDesign.model_fields:
                column = Track.experimental_design[triple.field].astext
            elif triple.field == "cell":
                biosampleFilter = Triple(
                    field="biosample_type", operator="like", value="cell"
                )
                statement = self.__add_statement_filters(statement, [biosampleFilter])
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
    def __set_query_target(responseType: ResponseContent):
        match responseType:
            case ResponseContent.IDS:
                return Track.track_id
            case ResponseContent.COUNTS:
                return func.count(Track.track_id)
            case ResponseContent.URLS:
                return Track.file_properties["url"]
            case _:
                return Track

    async def query_track_metadata(
        self,
        assembly: str,
        filters: Optional[List[str]],
        keyword: Optional[str],
        responseType: ResponseContent,
        limit: int = None,
        offset: int = None,
    ) -> List[Track]:

        target = self.__set_query_target(responseType)
        statement = (
            select(target)
            .filter(col(Track.genome_build) == assembly)
            .filter(col(Track.data_store).in_(self.__dataStore))
        )

        if filters is not None:
            statement = self.__add_statement_filters(statement, filters)
        if keyword is not None:
            statement = statement.filter(
                col(Track.searchable_text).regexp_match(keyword, "i"),
            )

        if responseType != ResponseContent.COUNTS:
            statement = statement.order_by(Track.track_id)

        if limit != None:
            statement = statement.limit(limit)

        if offset != None:
            statement = statement.offset(offset)

        result = await self.__session.execute(statement)

        if responseType == ResponseContent.COUNTS:
            return {"num_tracks": result.scalars().one()}
        else:
            return result.scalars().all()

    async def get_track_filter_summary(
        self, filterField: str, inclCounts: Optional[bool] = False
    ) -> dict:

        modelField = filterField  # FIXME: TRACK_SEARCH_FILTER_FIELD_MAP[filterField]["model_field"]

        valueCol = col(getattr(Track, modelField))
        if "biosample" in modelField:
            valueCol = valueCol["tissue_category"].astext
        # statement = select(valueCol, Track.track_id).group_by(valueCol).count()
        statement = (
            select(distinct(valueCol), func.count(Track.track_id))
            .where(valueCol.is_not(None))
            .group_by(valueCol)
            if inclCounts
            else select(distinct(valueCol)).where(valueCol.is_not(None))
        )

        result = (await self.__session.execute(statement)).all()
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
            col(Track.track_id).in_(tracks)
        )

        result = (await self.__session.execute(statement)).all()
        if len(result) > 1:
            statement = (
                select(Track.track_id, Track.genome_build)
                .where(col(Track.track_id).in_(tracks))
                .order_by(Track.genome_build, Track.track_id)
            )
            result = (await self.__session.execute(statement)).all()
            return {row[0]: row[1] for row in result}
        else:
            return result[0][0]
