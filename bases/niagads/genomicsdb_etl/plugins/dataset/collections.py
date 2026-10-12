from datetime import datetime
from fileinput import filename
import hashlib
import json
from typing import Optional
from niagads.common.models.base import CustomBaseModel, SerializationOptions
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import RAGDocType
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.mixins import (
    EmbeddingGeneratorContextMixin,
    ExternalDatabaseContextMixin,
)
from niagads.etl.plugins.parameters import BasePluginParams, EmbeddingParameterMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefParamMixin,
)
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import regex_replace
from pydantic import ConfigDict, Field
from sqlalchemy import select


class ShardedTrack(CustomBaseModel):
    track_id: int
    id: str
    file_name: str
    is_filer_track: bool
    collection_name: Optional[str] = None
    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrackCollectionLinkRecord(CustomBaseModel, arbitrary_types_allowed=True):
    collection: Collection
    track_ids: list[int]


class EmbeddedCollectionRecord(CustomBaseModel, arbitrary_types_allowed=True):
    collection: Collection
    chunk_text: str
    chunk_hash: bytes
    document_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch


class CollectionLoaderParams(ExternalDatabaseRefParamMixin, EmbeddingParameterMixin):
    """Parameters for CollectionLoader plugin."""

    name: str = Field(
        ...,
        description="collection name",
    )
    description: str = Field(
        ...,
        description="collection description",
    )
    key: str = Field(
        ..., description="short identifier for the collection, ideally unique"
    )
    source_id: Optional[str] = Field(
        default=None,
        description="collection identifier (e.g., accession) in original datasource (xdbref)",
    )


class CollectionLoaderBase(
    AbstractBasePlugin, ExternalDatabaseContextMixin, EmbeddingGeneratorContextMixin
):

    def __init__(
        self,
        params: BasePluginParams,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

    async def on_run_start(self, session) -> None:
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)

        if self.is_etl_run:
            await self.set_table_ref(session, Track)

    def _generate_embedded_collection_record(
        self, collection: Collection
    ) -> EmbeddedCollectionRecord:
        """Serialize a collection and prepare its embedding metadata.

        Args:
            collection (Collection): collection to serialize.

        Returns:
            EmbeddedCollectionRecord: Serialized collection record with content hashes.
        """
        try:
            chunk_text = json.dumps(
                collection.model_dump(
                    exclude_none=True,
                    context={SerializationOptions.EMBEDDED_TEXT: True},
                )
            )
        except Exception as err:
            self.logger.critical(f"Problem generating chunk_text for record: {err}")

        # self.logger.debug(f"Chunk Text: {chunk_text}")

        document = json.dumps(collection.model_dump(exclude_none=True))

        # generate embeddings
        embeddings = self._embedding_generator.generate(
            chunk_text,
            as_list=True,
        )
        return EmbeddedCollectionRecord(
            collection=collection,
            chunk_text=chunk_text,
            chunk_hash=self._embedding_generator.hash_text(chunk_text),
            document_hash=self._embedding_generator.hash_text(document),
            embedding=embeddings[0],
        )

    def get_record_id(self, record: EmbeddedCollectionRecord):
        return record.collection.collection_key


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Loads collection metadata.",
        affected_tables=[Collection],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=CollectionLoaderParams,
    )
)
class CollectionLoader(CollectionLoaderBase):
    _params: CollectionLoaderParams

    def extract(self) -> Collection:
        return Collection(
            name=self._params.name,
            description=self._params.description,
            collection_key=self._params.key,
            source_id=self._params.source_id,
        )

    async def transform(self, collection: Collection):
        return self._generate_embedded_collection_record(collection)

    async def load(self, session, record: EmbeddedCollectionRecord):
        record.collection.run_id = self.run_id
        record.collection.external_database_id = self.external_database_id
        collection_pk = await record.collection.submit(session)

        chunk_metadata: ChunkMetadata = ChunkMetadata(
            table_id=self._table_ref.table_id,
            row_id=collection_pk,
            document_type=str(RAGDocType.METADATA),
            document_hash=record.document_hash,
            chunk_hash=record.chunk_hash,
            chunk_text=record.chunk_text,
            run_id=self.run_id,
        )
        chunk_metadata_id = await chunk_metadata.submit(session)
        chunk_embedding: ChunkEmbedding = ChunkEmbedding(
            chunk_metadata_id=chunk_metadata_id,
            chunk_hash=record.chunk_hash,
            embedding_model=str(self._params.embedding_model),
            embedding=record.embedding,
            embedding_date=datetime.now().isoformat(),
            embedding_run_id=self.run_id,
            run_id=self.run_id,
        )
        await chunk_embedding.submit(session)

        return self.create_checkpoint(record=record)


# FIXME: needs to do embedding
@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Identifies sharded tracks from an ETL Run in {Track.table_name()} and populates Collections and links for each shard group table.",
        affected_tables=[TrackCollectionLink, Collection],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=BasePluginParams,
    )
)
class ShardCollectionLoader(AbstractBasePlugin):

    def __init__(
        self,
        params: BasePluginParams,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        raise NotImplementedError(
            "This plugin must be updated to inherit from shared loader base and generate embeddings"
        )
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
        records: dict[str, TrackCollectionLinkRecord] = {}
        for track in tracks:
            track.collection_name = regex_replace(
                RegularExpressions.SHARD, "_", filename
            )
            if track.collection_name not in records:
                collection_key = f"SHARD_GROUP_{
                    hashlib.sha512(track.collection_name.encode("utf-8"))
                    .hexdigest()[:6]
                    .upper()}"

                records[track.collection_name] = TrackCollectionLinkRecord(
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

    def get_record_id(self, record: TrackCollectionLinkRecord):
        return f"{record.collection.collection_key}:{record.collection.name}"

    async def load(self, session, records: list[TrackCollectionLinkRecord]):

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
