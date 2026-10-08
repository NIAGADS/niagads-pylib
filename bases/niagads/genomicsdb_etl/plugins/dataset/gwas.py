"""
GWASTrackLoader Plugin
- Loads a Track record from TrackRecord-compliant JSON file into the Track table.
- (optionally) assigns track to a collection based on collection key (e.g., NIAGADS Dataset Accession)
-
"""

from collections import defaultdict
from typing import Any, Dict, Iterator, Optional

from niagads.database.genomicsdb.schema.dataset.collection import (
    TrackCollectionLink,
    Collection,
)
from niagads.database.genomicsdb.schema.results.associations import VariantAssociation
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import (
    Track,
    TrackConcept,
    TrackContext,
)


from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.bases.features import BinIndexReferenceMixin
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)

from niagads.genomicsdb_etl.plugins.variant.base import VariantLookupMixin
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
    collection: str = Field(
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
        description=f"Loads variant associations with genome-wide significance from "
        f" a hipFG standardized summary statistics file into {VariantAssociation.table_name()} "
        " as well as associated track metadata and collection affiliation.",
        affected_tables=[
            VariantAssociation,
            ChunkMetadata,
            ChunkEmbedding,
            TrackCollectionLink,
            TrackConcept,
            TrackContext,
            Track,
        ],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=GWASTrackLoaderParams,
    )
)
class GWASTrackLoader(TrackLoaderBase, VariantLookupMixin, BinIndexReferenceMixin):

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
        self._track_record: TrackRecord = None
        self._track_collection_pk: int = None
        self._bin_index_reference: dict = defaultdict(
            lambda: defaultdict(lambda: {"starts": [], "bins": []})
        )

    async def on_run_start(self, session):
        """Initialize track type and prepare for ETL run."""
        await super().on_run_start(session)

        # done here so we have it and preprocess/extract can focus on the data
        self._track_record = self._extract_track_record(self._params.metadata_file)

        if self.is_etl_run:  # requires DB connection
            # validate collection and get primary key
            self._track_collection_pk = await Collection.find_primary_key(
                session, filters={"collection_key": self._params.collection}
            )

            # validate ontology terms and presence of required fields in track JSON file
            ot_validation_file_path = f"{self._params.metadata_file}.ot_validation.json"
            is_valid: bool = await self._validate_track_record(
                self._track_record, ot_validation_file_path
            )
            if not is_valid:
                raise ValueError(
                    f"Invalid Track JSON {self._params.metadata_file}. "
                    f"Please see log and {ot_validation_file_path}"
                    "ontology-term validation file for details."
                )

            # bin index for variant lookups
            await self._fetch_bin_index_mapping(session)

    async def preprocess(self) -> None:
        # extract gwas significant,
        # calculate -log10p and beta sign, extract test allele if < 50bp

        # map to db
        # identify missing
        # identify not annotated
        # bin_index if new or save for load time?
        ...

    def extract(self) -> Iterator[TrackRecord]: ...

    async def transform(self, record: TrackRecord) -> TrackRecord:
        self._transform
        return record

    async def load(self, session, association_records: list[VariantAssociation]):
        embedded_track_records = self._embed_track_records([self._track_record])
        tracks: list[Track] = await self._load_track_records(embedded_track_records)

        track_id: int = tracks[0].track_id
