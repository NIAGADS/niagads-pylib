"""
GWASTrackLoader Plugin
- Loads a Track record from TrackRecord-compliant JSON file into the Track table.
- (optionally) assigns track to a collection based on collection key (e.g., NIAGADS Dataset Accession)
-

Expected incoming fileds
#chrom  position        variant_id      ref     alt     pval    OR      z_score effect_size     effect_size_se  non_ref_af      rsid    QC_flags        user_input
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, Iterator, Optional

from niagads.common.models.base import CustomBaseModel
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
from niagads.genome_reference.human import HumanGenome
from niagads.genomicsdb_etl.plugins.common.bases.features import BinIndexReferenceMixin
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)

from niagads.genomicsdb_etl.plugins.variant.base import VariantLookupMixin
from niagads.utils.numeric import to_scientific_notation
from niagads.utils.sys import read_open_ctx
from pydantic import Field


class GWASAssocationEntry(CustomBaseModel):
    chromosome: HumanGenome
    position: int
    variant_id: str
    test_allele: Optional[str] = None
    pvalue: str
    decimal_pvalue: Decimal
    neg_log10_pvalue: float
    effect_direction: Optional[str] = None

    def __effect_direction(self, effect_size: float) -> str:
        if effect_size is None:
            return None
        else:
            "-" if effect_size < 0 else "+"

    @classmethod
    def from_hipFG_entry(cls, entry: dict):
        decimal_pvalue = Decimal(entry["pval"])
        test_allele = entry["alt"]

        return cls(
            chromsome=entry["chrom"],
            position=entry["position"],
            variant_id=entry["variant_id"],
            test_allele=test_allele if len(test_allele) <= 50 else None,
            neg_log10_pvalue=f"{-1 * decimal_pvalue.log10():.2f}",
            pvalue=to_scientific_notation(decimal_pvalue),
            decimal_pvalue=decimal_pvalue,
            effect_direction=cls.__effect_direction(entry["effect_size"]),
        )


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
    pvalue_cutoff: float = Field(
        default=1e-3, description="(relaxed) cutoff of genome-wide significance"
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

    def extract(self) -> Iterator[dict]:
        self.logger.info(
            f"Extracting Associations with Genome-Wide Significance (p <= {self._params.pvalue_cutoff})"
        )

        decimal_threshold = Decimal(self._params.pvalue_cutoff)

        num_significant_associations = 0
        with read_open_ctx(self._params.data_file) as fh:
            header_fields = next(fh).rstrip().lstrip("#").split("\t")
            for line_num, line in enumerate(fh):
                values = line.rstrip().split("\t")
                hipfg_entry = dict(zip(header_fields, values))

                if line_num % 500000 == 0:
                    self.logger.info(f"Parsed {line_num} lines.")

                entry = GWASAssocationEntry.from_hipFG_entry(hipfg_entry)
                if entry.decimal_pvalue < decimal_threshold:
                    num_significant_associations += 1
                    yield entry

        self.logger.info(
            f"Done extracting associations.  Found {num_significant_associations} significant associations"
        )

    async def transform(self, data: GWASAssocationEntry) -> GWASAssocationEntry:
        return data

    async def load(self, session, entries: list[GWASAssocationEntry]):
        embedded_track_records = self._embed_track_records([self._track_record])
        tracks: list[Track] = await self._load_track_records(embedded_track_records)

        track_id: int = tracks[0].track_id

        # now we need to lookup the variants and log unannotated
