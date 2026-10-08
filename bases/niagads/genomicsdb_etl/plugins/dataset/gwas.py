"""
GWASTrackLoader Plugin
- Loads a Track record from TrackRecord-compliant JSON file into the Track table.
- (optionally) assigns track to a collection based on collection key (e.g., NIAGADS Dataset Accession)
-
"""

from typing import Any, Dict, Iterator, Optional

from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import Track


from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)

from pydantic import Field


class GWASTrackLoaderParams(TrackLoaderBaseParams, PathValidatorMixin):
    """Parameters for TrackJSONLoader plugin."""

    metadata_file: str = Field(
        ...,
        description="full path to TrackRecord-compliant JSON file",
    )
    data_file: str = Field(
        ...,
        description="full path to TrackRecord-compliant JSON file",
    )
    collection_key: str = Field(
        ..., description="collection key; e.g., dataset accession for the track"
    )
    pvalue_threshold: float = Field(
        default=5e-8, description="cutoff of genome-wide significance"
    )

    validate_metadata_exists = PathValidatorMixin.validator("metadata_file")
    validate_data_exists = PathValidatorMixin.validator("data_file")


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"",
        affected_tables=[Track],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=GWASTrackLoaderParams,
    )
)
class GWASTrackLoader(TrackLoaderBase):

    _params: GWASTrackLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

    async def on_run_start(self, session):
        """Initialize track type and prepare for ETL run."""
        await super().on_run_start(session)
        self._load_track_record(self._params.track_metadata)
        self._validate_track_record()

    async def preprocess(self) -> None:
        # validate track record format and ontology terms
        self.logger.info(f"Validate track metadata filie: {self._params.file}")
        track_record = self._load_track_record(self._params.file)
        await self._validate_track_record(track_record)

        # preprocessing input data

    def extract(self) -> Iterator[TrackRecord]: ...

    async def transform(self, record: TrackRecord) -> TrackRecord:
        return record

    async def load(self, session, records: list[TrackRecord]): ...
    def on_run_complete(self): ...
