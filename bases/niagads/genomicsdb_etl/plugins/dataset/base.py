from typing import Any, Dict, Optional


from niagads.common.models.base import CustomBaseModel
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import Track

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
