# TODO: Parse and Load ontology Terms
# TODO: investigate DASH2 and UCSC tracks

import json
from datetime import datetime
from typing import Any, Dict, Optional

from niagads.common.models.base import CustomBaseModel, SerializationOptions
from niagads.common.reference.xrefs.data_sources import NIAGADSResources
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import RAGDocType
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.mixins import (
    EmbeddingGeneratorContextMixin,
    ExternalDatabaseContextMixin,
)
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    EmbeddingParameterMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.metadata_parser.filer import MetadataTemplateParser
from niagads.requests.core import HttpClientSessionManager
from niagads.utils.list import chunker
from niagads.utils.sys import read_open_ctx
from pydantic import Field


class EmbeddedTrackRecord(CustomBaseModel, arbitrary_types_allowed=True):
    track: TrackRecord
    chunk_text: str
    chunk_hash: bytes
    document_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch


class TrackLoaderBaseParams(
    BasePluginParams,
    ExternalDatabaseRefMixin,
    EmbeddingParameterMixin,
): ...


class TrackLoaderBase(
    AbstractBasePlugin, ExternalDatabaseContextMixin, EmbeddingGeneratorContextMixin
):
    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._database_type_id: int = None

    async def on_run_start(self, session):
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)

        await self.set_table_ref(session, Track)

    def get_record_id(self, erecord: EmbeddedTrackRecord):
        return erecord.track.id


class FILERTrackLoaderParams(TrackLoaderBaseParams):
    filer_service_url: Optional[str] = Field(
        default=NIAGADSResources.FILER_SERVICE_URL.value,
        description="FILER service (API) URL; use to validate live tracks",
    )
    filer_download_url: Optional[str] = Field(
        default=NIAGADSResources.FILER_DOWNLOAD_URL.value,
        description="FILER download URL, not accessed; used to generate download links",
    )
    skip_live_validation: Optional[bool] = Field(
        default=False,
        description="skip validating live tracks against the FILER service",
    )
    template_file: str = Field(
        ...,
        description="full path to input file, may also be full URL path in FILER service",
    )
    filer_genome_build: Optional[str] = Field(
        default="hg38",
        description="FILER genome build of data annotated by the template; one of hg38, hg38.lifted, hg19",
    )
    live_metadata_cache: Optional[str] = Field(
        default=None, description="local cache of live file metadata"
    )


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Parses and loads FILER metadata template file into the {Track.table_name()} table.",
        affected_tables=[Track],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=FILERTrackLoaderParams,
    )
)
class FILERTrackLoader(TrackLoaderBase):
    _EXCLUDED_DATASOURCES = [
        "RefSeq",
        "1K Genome Phase3",
        "dbSNP",
        "RefSeq",
        "HOMER",
        "Inferno",
        "Gencode",
        "CADD",
        "GWAS_Catalog",
        "Ensembl",
        "CADD",
        "UCSC",
        "DASHR2",  # FIXME: something is wrong w/their name generation
    ]
    _FILER_METADATA_ENDPOINT = "get_metadata.php"
    _DATASET_TYPE_CURIE: str = "EDAM:topic_0085"  # FIX ME - temporary

    _params: FILERTrackLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        self.__live_tracks_ref = None

    async def __fetch_live_track_ids(self):
        """Fetch live FILER track identifiers reference."""

        if self._params.live_metadata_cache is not None:
            self.logger.info(
                f"Loading live tracks for {self._params.live_metadata_cache}"
            )
            with read_open_ctx(self._params.live_metadata_cache) as fh:
                response = json.load(fh)
        else:
            self.logger.info(
                f"Fetching live tracks for {self._params.filer_genome_build} from {self._params.filer_service_url}"
            )
            async with HttpClientSessionManager(
                self._params.filer_service_url,
                debug=self._debug,
                verbose=self._verbose,
                logger=self.logger,
                timeout=300,
            ) as session_manager:
                params = {"genomeBuild": self._params.filer_genome_build}
                response: dict = await session_manager.fetch_json(
                    self._FILER_METADATA_ENDPOINT, params
                )

        self.__live_tracks_ref = {t["identifier"]: True for t in response}

        self.logger.info(
            f"Retrieved {len(self.__live_tracks_ref)} {self._params.filer_genome_build} live tracks for validation."
        )

    async def on_run_start(self, session):
        await super().on_run_start(session)
        if not self._params.skip_live_validation:
            await self.__fetch_live_track_ids()

        self._dataset_type_id = await OntologyTerm.find_primary_key(
            session, curie=self._DATASET_TYPE_CURIE
        )

    def __exclude_track(self, record: TrackRecord):
        """Determine if a track should be skipped."""

        msg_prefix: str = f"SKIPPED {record.id}:{record.name}"
        reason: str = None
        exclude: bool = False

        if not self.__live_tracks_ref:
            if record.id not in self.__live_tracks_ref:
                exclude = True
                reason = f"Not Live"
        else:
            matched_excluded_datasource = None
            data_source = getattr(record.provenance, "data_source")
            if data_source is not None and data_source in self._EXCLUDED_DATASOURCES:
                matched_excluded_datasource = data_source
            else:
                matched_excluded_datasource = next(
                    (
                        s
                        for s in self._EXCLUDED_DATASOURCES
                        if record.name.startswith(s)
                    ),
                    None,
                )

            if matched_excluded_datasource is not None:
                exclude = True
                reason = f"Excluded Datasource: {matched_excluded_datasource}"
            elif record.genome_build is None:
                exclude = True
                reason = "No Genome Build"
            elif "Not applicable" in record.name:
                if not record.is_download_only:
                    raise ValueError(
                        f"Malformed queryable track name: {record}.  Please review and correct or update skip_track criteria to proceed."
                    )

        if exclude:
            if self._verbose:
                self.logger.warning(f"{msg_prefix}: {reason}")
                self.logger.debug(f"{msg_prefix}: {reason}")

        return exclude

    def extract(self):
        parser: MetadataTemplateParser = MetadataTemplateParser(
            template_file=self._params.template_file,
            filer_download_url=self._params.filer_download_url,
            debug=self._debug,
            verbose=self._verbose,
            logger=self.logger,
        )

        parser.parse()

        records = [
            record
            for record in parser.to_track_records()
            if not self.__exclude_track(record)
        ]

        self.logger.info(f"Extracted {len(records)} valid records.")
        return records

    def __generate_embedded_track_record(
        self, record: TrackRecord
    ) -> EmbeddedTrackRecord:
        try:
            chunk_text = json.dumps(
                record.model_dump(
                    exclude_none=True,
                    context={SerializationOptions.EMBEDDED_TEXT: True},
                )
            )
        except Exception as err:
            self.logger.critical(f"Problem generating chunk_text for record: {err}")

        # self.logger.debug(f"Chunk Text: {chunk_text}")

        document = json.dumps(record.model_dump(exclude_none=True))

        return EmbeddedTrackRecord(
            track=record,
            chunk_text=chunk_text,
            chunk_hash=self._embedding_generator.hash_text(chunk_text),
            document_hash=self._embedding_generator.hash_text(document),
        )

    async def transform(self, records: list[TrackRecord]) -> list[EmbeddedTrackRecord]:
        # generate embeddings
        embedded_track_records: list[EmbeddedTrackRecord] = [
            self.__generate_embedded_track_record(record) for record in records
        ]

        PROGRESS_INTERVAL = 10
        embeddings = []
        generated_count = 0
        for batch_index, chunk in enumerate(
            chunker(
                embedded_track_records,
                self._params.embedding_batch_size,
                return_iterator=False,
            )
        ):
            embedding_subset = self._embedding_generator.generate(
                [r.chunk_text for r in chunk],
                as_list=True,
            )
            embeddings += embedding_subset
            generated_count += len(chunk)

            if (batch_index + 1) % PROGRESS_INTERVAL == 0:
                self.logger.info(
                    f"Generated embeddings for {generated_count} / "
                    f"{len(embedded_track_records)} records"
                )

        for index, embedding in enumerate(embeddings):
            embedded_track_records[index].embedding = embedding

        return embedded_track_records

    async def load(self, session, records: list[EmbeddedTrackRecord]):

        tracks: list[Track] = []

        for record in records:
            tracks.append(
                Track(
                    **record.track.model_dump(exclude=["id"]),
                    source_id=record.track.id,
                    dataset_type_id=self._dataset_type_id,
                    run_id=self.run_id,
                    external_database_id=self.external_database_id,
                )
            )

        await Track.submit_many(session, tracks)

        chunk_metadata: list[ChunkMetadata] = []
        for index, record in enumerate(records):
            chunk_metadata.append(
                ChunkMetadata(
                    table_id=self._table_ref.table_id,
                    row_id=tracks[index].track_id,
                    document_type=str(RAGDocType.METADATA),
                    document_hash=record.document_hash,
                    chunk_hash=record.chunk_hash,
                    chunk_text=record.chunk_text,
                    run_id=self.run_id,
                )
            )

        await ChunkMetadata.submit_many(session, chunk_metadata)

        chunk_embeddings: list[ChunkEmbedding] = []
        for index, metadata in enumerate(chunk_metadata):
            chunk_embeddings.append(
                ChunkEmbedding(
                    chunk_metadata_id=metadata.chunk_metadata_id,
                    chunk_hash=metadata.chunk_hash,
                    embedding_model=str(self._params.embedding_model),
                    embedding=records[index].embedding,
                    embedding_date=datetime.now().isoformat(),
                    embedding_run_id=self.run_id,
                    run_id=self.run_id,
                )
            )

        await ChunkEmbedding.submit_many(session, chunk_embeddings)

        return self.create_checkpoint(record=records[-1])


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Loads a {TrackRecord}-compliant JSON file in to {Track.table_name()}.",
        affected_tables=[Track],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=TrackLoaderBaseParams,
    )
)
class TrackJSONLoader(TrackLoaderBase): ...
