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

from niagads.common.models.base import CustomBaseModel, SerializationOptions
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)
from niagads.database.genomicsdb.schema.dataset.track import (
    Track,
    TrackConcept,
    TrackContext,
)
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.results.associations import VariantAssociation
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    GA4GHParamMixin,
    PathValidatorParamMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.ga4gh.annotators import PrimaryKeyGenerator
from niagads.genome_reference.human import HumanGenome
from niagads.genomicsdb_etl.plugins.common.mixins.intervals import (
    BinIndexReferenceMixin,
)
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)
from niagads.genomicsdb_etl.plugins.variant.vcf_loaders.base import (
    VariantPrimaryKeyGeneratorMixin,
)
from niagads.utils.list import qw
from niagads.utils.numeric import to_scientific_notation
from niagads.utils.sys import read_open_ctx, timer, verify_path
from niagads.vcf.types import VCFEntry
from pydantic import Field


class GWASAssocationEntry(CustomBaseModel):
    chromosome: HumanGenome
    position: int
    variant_id: str
    test_allele: Optional[str] = None
    alt: str = None
    ref: str = None
    pvalue: str
    decimal_pvalue: Decimal
    neg_log10_pvalue: float
    effect_direction: Optional[str] = None
    entry_id: str

    @classmethod
    def __effect_direction(cls, effect_size: float) -> str:
        if effect_size is None:
            return None
        else:
            return "-" if effect_size < 0 else "+"

    @classmethod
    def from_hipFG_entry(cls, entry: dict, line_num: int, is_zero_based: bool = False):
        decimal_pvalue = Decimal(entry["pval"])
        test_allele = entry["alt"]
        position = (
            int(entry["position"]) + 1 if is_zero_based else int(entry["position"])
        )

        assoc_entry = cls(
            chromosome=HumanGenome(entry["chrom"]),
            position=position,
            variant_id=entry["variant_id"],
            test_allele=test_allele if len(test_allele) <= 50 else None,
            alt=entry["alt"],
            ref=entry["ref"],
            neg_log10_pvalue=f"{-1 * decimal_pvalue.log10():.2f}",
            pvalue=to_scientific_notation(decimal_pvalue),
            decimal_pvalue=decimal_pvalue,
            effect_direction=cls.__effect_direction(float(entry["effect_size"])),
            entry_id=f"line={int(line_num)};variant={entry['variant_id']}",
        )

        if is_zero_based:
            assoc_entry.variant_id = f"{str(assoc_entry.chromosome.value)}:{position}:{assoc_entry.ref}:{assoc_entry.alt}"
            assoc_entry.entry_id = (
                f"line={int(line_num)};variant={assoc_entry.variant_id}"
            )

        return assoc_entry

    def to_vcf_entry(self) -> VCFEntry:
        return VCFEntry(
            chrom=self.chromosome,
            pos=self.position,
            id=self.variant_id,
            ref=self.ref,
            alt=self.alt,
        )

    def to_delimited_text(
        self, *, fields=None, incl_header=False, null_str=".", delimiter="\t"
    ):
        return self.to_vcf_entry().to_delimited_text(
            fields=fields, incl_header=incl_header
        )


class GWASTrackLoaderParams(
    TrackLoaderBaseParams, PathValidatorParamMixin, GA4GHParamMixin
):
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
    pvalue_cutoff: Optional[float] = Field(
        default=1e-3, description="(relaxed) cutoff of genome-wide significance"
    )

    is_zero_based: Optional[bool] = Field(
        default=False,
        description="temporary patch to handle a few zero-based hipFG files",
    )

    validate_metadata_exists = PathValidatorParamMixin.validator("metadata_file")
    validate_data_exists = PathValidatorParamMixin.validator("data_file")


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Loads variant associations with genome-wide significance from "
        f" a hipFG standardized summary statistics file into {VariantAssociation.table_name()} "
        " as well as associated track metadata and collection affiliation. Will load novel "
        " variants into Variant.Variant",
        affected_tables=[
            Variant,
            VariantAssociation,
            ChunkEmbedding,
            ChunkMetadata,
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
class GWASTrackLoader(
    TrackLoaderBase,
    BinIndexReferenceMixin,
    VariantPrimaryKeyGeneratorMixin,
):

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
        self._current_chromosome: HumanGenome = None
        self._unannotated_variant_vcf_fh = None
        self._variant_pk_generator: PrimaryKeyGenerator = None
        self._track_pk: int = None
        self._num_unnannotated_variants = 0

    async def on_run_start(self, session):
        """Initialize track type and prepare for ETL run."""
        await super().on_run_start(session)
        await VariantPrimaryKeyGeneratorMixin.on_run_start(self, session)

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

            # create fh for unnannotated variants VCF and write header
            file_name: str = f"{self._params.data_file}.unannotated-variants.vcf"
            if verify_path(file_name):
                self.logger.warning(
                    f"Unannotated Variant VCF file: {file_name} already exists.  Overwriting."
                )
            self._unannotated_variant_vcf_fh = open(file_name, "w")

            # developer note: can't use f-string here b/c backslash not allowed
            print(
                "#" + "\t".join(qw("CHROM POS ID REF ALT QUAL FILTER INFO")),
                file=self._unannotated_variant_vcf_fh,
                flush=True,
            )

    def extract(self) -> Iterator[dict]:
        self.logger.info(
            f"Extracting Associations with Genome-Wide Significance (p <= {self._params.pvalue_cutoff})"
        )

        decimal_threshold = Decimal(self._params.pvalue_cutoff)

        num_significant_associations = 0

        with read_open_ctx(self._params.data_file) as fh:
            header_fields = next(fh).rstrip().lstrip("#").split("\t")
            for line_num, line in enumerate(fh, start=1):
                values = line.rstrip().split("\t")
                hipfg_entry = dict(zip(header_fields, values))

                if line_num % 500000 == 0:
                    self.logger.info(f"Parsed {line_num} lines.")
                    self.logger.info(
                        f"Detected {num_significant_associations} significant associations."
                    )

                entry = GWASAssocationEntry.from_hipFG_entry(
                    hipfg_entry, line_num, self._params.is_zero_based
                )

                if entry.decimal_pvalue <= decimal_threshold:
                    num_significant_associations += 1
                    # self.logger.critical(f"Parsed Passing Entry: {entry.model_dump()}")
                    yield entry

        self.logger.info(
            f"Done extracting associations.  Found {num_significant_associations} significant associations."
        )

    async def transform(self, data: GWASAssocationEntry) -> GWASAssocationEntry:
        return data

    async def _load_variant(self, session, entry: GWASAssocationEntry) -> Variant:
        record: VariantRecord = self._generate_variant_identifier_record(
            entry.to_vcf_entry(), require_validation=False  # trust hipFG
        )

        try:
            variant = Variant.from_variant_record(record)
        except Exception as err:
            if variant is not None:
                self.logger.critical(f"Malformed Variant Record: {record.model_dump(
                        exclude_none=True,
                        context={SerializationOptions.ENUMS_AS_NAME: True},
                    )}: {str(err)}")
            else:
                raise err

        variant.run_id = self.run_id
        variant.bin_index = self._find_bin_index(str(record.chromosome), record.span)
        variant.external_database_id = self.external_database_id
        await variant.submit(session)

        return variant

    async def _get_variant_db_record(
        self, session, entry: GWASAssocationEntry
    ) -> Variant:
        vcf_entry = entry.to_vcf_entry()
        if vcf_entry.is_structural_variant:
            record: VariantRecord = self._generate_variant_identifier_record(
                vcf_entry, require_validation=False  # trust hipFG
            )
            lookup_id = record.id
        else:
            lookup_id = vcf_entry.positional_id

        try:
            match: Variant = await Variant.fetch_record(
                session, {"niagads_id": lookup_id}
            )
        except:
            return None  # not found

        return match

    async def _load_track_collection_link(self, session, track_id: int):
        tc_link = TrackCollectionLink(
            track_id=track_id,
            collection_id=self._track_collection_pk,
            run_id=self.run_id,
        )
        await tc_link.submit(session)

    async def load(self, session, entries: list[GWASAssocationEntry]):
        if not self._track_pk:
            # in non-commit mode, commits will get rolled back between
            # calls to chunked load, so the "track" will get removed from the
            # database.  so it will need to be reinserted
            embedded_track_records = self._embed_track_records([self._track_record])
            tracks: list[Track] = await self._load_track_records(
                session, embedded_track_records
            )

            self._track_pk = tracks[0].track_id
            await self._load_track_collection_link(session, self._track_pk)

        else:
            if not self._params.commit:
                self.logger.critical(
                    "Cannot test multiple batches in non-commit mode: track_id lost during rollback."
                )

        # data are so sparse, trying single lookups - hopefull faster
        associations = []

        num_new_variants = 0
        for entry in entries:
            variant: Variant = await self._get_variant_db_record(session, entry)
            is_annotated: bool = variant is not None and variant.is_annotated
            if variant is None:  # novel variant
                # need to load and in Variant.Variant and write to file to be annotated
                variant: Variant = await self._load_variant(session, entry)
                num_new_variants += 1

            if not is_annotated:
                entry.variant_id = variant.niagads_id
                print(
                    entry.to_delimited_text(),
                    file=self._unannotated_variant_vcf_fh,
                    flush=True,
                )
                self._num_unnannotated_variants += 1

            # build the association entry
            associations.append(
                VariantAssociation(
                    track_id=self._track_pk,
                    variant_id=variant.variant_id,
                    variant_stable_id=variant.niagads_id,
                    neg_log10_pvalue=entry.neg_log10_pvalue,
                    pvalue=entry.pvalue,
                    effect_direction=entry.effect_direction,
                    test_allele=entry.test_allele,
                    run_id=self.run_id,
                    chromosome=str(entry.chromosome),
                    bin_index=variant.bin_index,
                    span=variant.span,
                )
            )

        if num_new_variants / len(entries) >= 0.80:
            raise ValueError(
                "80% or more of the variants could not be mapped to the database; are positions 0-based?"
            )

        await VariantAssociation.submit_many(session, associations)

        return self.create_checkpoint(record=entries[-1])

    def get_record_id(self, record: GWASAssocationEntry) -> str:
        return record.entry_id

    async def on_run_complete(self):
        if (
            self._unannotated_variant_vcf_fh
            and not self._unannotated_variant_vcf_fh.closed
        ):
            self._unannotated_variant_vcf_fh.close()

        self.logger.info(
            f"To be annotated variants: {self._unannotated_variant_vcf_fh.name}"
        )
        self.logger.info(
            f"Number unannotated variants: {self._num_unnannotated_variants}"
        )
