# TODO: Parse and Load ontology Terms
# TODO: investigate DASH2 and UCSC tracks

import json

from typing import Any, Dict, Optional

from niagads.genomicsdb_etl.plugins.dataset.base import (
    EmbeddedTrackRecord,
    TrackLoaderBase,
    TrackLoaderBaseParams,
)


from niagads.common.reference.xrefs.data_sources import NIAGADSResources
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)

from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm

from niagads.etl.plugins.metadata import PluginMetadata

from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy

from niagads.metadata_parser.filer import MetadataTemplateParser
from niagads.requests.core import HttpClientSessionManager
from niagads.utils.sys import read_open_ctx
from pydantic import Field


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
        affected_tables=[ChunkEmbedding, ChunkMetadata, Track],
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
    _TRACK_TYPE_CURIE: str = "EDAM:topic_0085"  # FIX ME - temporary

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

        self._track_type_id = await OntologyTerm.find_primary_key(
            session, curie=self._TRACK_TYPE_CURIE
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

        records = []
        record_count = 0
        for record in parser.to_track_records():
            if self.__exclude_track(record):
                continue

            records.append(record)
            record_count += 1

            if len(records) == self._params.embedding_batch_size:
                yield records
                records = []

        if records:
            yield records

        self.logger.info(f"Extracted {record_count} valid records.")

    async def transform(self, records: list[TrackRecord]) -> list[EmbeddedTrackRecord]:
        return self._embed_track_records(records)

    async def load(self, session, records: list[EmbeddedTrackRecord]):
        await self._load_track_records(session, records, is_filer_track=True)
        self.create_checkpoint(record=records[-1])
