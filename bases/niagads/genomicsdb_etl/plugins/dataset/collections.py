from fileinput import filename
import hashlib
from typing import Optional
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import regex_replace
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Identifies sharded tracks from an ETL Run in {Track.table_name()} and populates Collections for each shard group table.",
        affected_tables=[TrackCollectionLink, Collection],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=BasePluginParams,
    )
)
class ShardedTrack(BaseModel):
    track_id: int
    id: str
    file_name: str
    is_filer_track: bool
    collection_name: Optional[str] = None
    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CollectionRecord(BaseModel, arbitrary_types_allowed=True):
    collection: Collection
    track_ids: list[int]


class ShardCollectionLoader(AbstractBasePlugin):

    def __init__(
        self,
        params: BasePluginParams,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._sharded_tracks = {}

    async def on_run_start(self, session):
        stmt = select(
            Track.track_id,
            Track.id,
            Track.file_properties["file_name"].label("file_name"),
            Track.is_filer_track,
        ).where(Track.is_shard.is_(True))

        result = (await session.execute(stmt)).mappings().all()
        self._sharded_tracks = [ShardedTrack(**r) for r in result]

    def extract(self):
        if self.is_dry_run:
            raise ValueError(
                "No DRY_RUN available for this plugin; pulls data from the database."
            )

        return self._sharded_tracks

    async def transform(self, tracks: list[ShardedTrack]):
        records: dict[str, CollectionRecord] = {}
        for track in tracks:
            track.collection_name = regex_replace(
                RegularExpressions.SHARD, "_", filename
            )
            if track.collection_name not in records:
                collection_key = f"SHARD_GROUP_{
                    hashlib.sha512(track.collection_name.encode("utf-8"))
                    .hexdigest()[:6]
                    .upper()}"

                records[track.collection_name] = CollectionRecord(
                    collection=Collection(
                        collection_key=collection_key,
                        name=track.collection_name,
                        description=track.collection_name,
                        is_sharded_collection=True,
                        is_filer_collection=track.is_filer_track,
                        run_id=self.run_id,  # can set b/c data pulled from db
                    ),
                    track_ids=[track.id],
                )
            else:
                records[track.collection_name].track_ids.append(track.id)

        return records.values()

    def get_record_id(self, record: CollectionRecord):
        return f"{record.collection.collection_key}:{record.collection.name}"

    async def load(self, session, records: list[CollectionRecord]):

        links = []
        for record in records:
            if not Collection.record_exists(
                session, filters={"collection_key": record.collection.collection_key}
            ):
                collection_pk = record.collection.submit(session)
                for tid in record.track_ids:
                    links.append(
                        TrackCollectionLink(
                            track_id=tid,
                            collection_id=collection_pk,
                            run_id=self.run_id,
                        )
                    )
            else:
                self.logger.warning(f"Collection exists: {self.get_record_id(record)}")
                self.inc_tx_count(Collection, ETLOperation.SKIP)

        if links:
            TrackCollectionLink.submit_many(session, links)

        return self.create_checkpoint(record=records[-1])
