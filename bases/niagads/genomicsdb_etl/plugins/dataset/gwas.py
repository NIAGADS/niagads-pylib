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
from itertools import groupby
from operator import attrgetter
from typing import Any, Dict, Iterator, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
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
from niagads.etl.plugins.parameters import PathValidatorMixin, VariantIdGeneratorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.ga4gh.annotators import PrimaryKeyGenerator
from niagads.genome_reference.human import HumanGenome
from niagads.genomicsdb_etl.plugins.common.bases.features import BinIndexReferenceMixin
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)
from niagads.genomicsdb_etl.plugins.variant.base import (
    MatchedVariant,
    VariantLookupMap,
    VariantLookupMixin,
)
from niagads.utils.list import qw
from niagads.utils.numeric import to_scientific_notation
from niagads.utils.sys import read_open_ctx, verify_path
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

    def __effect_direction(self, effect_size: float) -> str:
        if effect_size is None:
            return None
        else:
            "-" if effect_size < 0 else "+"

    @classmethod
    def from_hipFG_entry(cls, entry: dict, line_num: int):
        decimal_pvalue = Decimal(entry["pval"])
        test_allele = entry["alt"]

        return cls(
            chromsome=HumanGenome(entry["chrom"]),
            position=entry["position"],
            variant_id=entry["variant_id"],
            test_allele=test_allele if len(test_allele) <= 50 else None,
            alt=entry["alt"],
            ref=entry["ref"],
            neg_log10_pvalue=f"{-1 * decimal_pvalue.log10():.2f}",
            pvalue=to_scientific_notation(decimal_pvalue),
            decimal_pvalue=decimal_pvalue,
            effect_direction=cls.__effect_direction(entry["effect_size"]),
            entry_id=f"line={int(line_num)};variant={entry['variant_id']}",
        )

    def to_delimited_text(
        self, *, fields=None, incl_header=False, null_str=".", delimiter="\t"
    ):
        return VCFEntry(**self.model_dump()).to_delimited_text(
            fields=fields, incl_header=incl_header
        )


class GWASTrackLoaderParams(
    TrackLoaderBaseParams, PathValidatorMixin, VariantIdGeneratorMixin
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
        " as well as associated track metadata and collection affiliation. Will load novel "
        " variants into Variant.Variant",
        affected_tables=[
            Variant,
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
        self._current_chromosome: HumanGenome = None
        self._unannotated_variant_vcf_fh = None
        self._variant_pk_generator: PrimaryKeyGenerator = None

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

            # initialize variant primary key generator
            self._variant_pk_generator = PrimaryKeyGenerator(
                genome_build=self._params.genome_build,
                seqrepo_data_proxy=self._params.seqrepo_data_proxy,
                logger=self.logger if self._verbose else None,
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
            )

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

    async def _load_variant(self, session, entry: GWASAssocationEntry):
        # needs to return the niagads_id (stable_id) and the db_pk
        pass

    def _get_variant_db_record(
        self, reference_variants: VariantLookupMap, entry: GWASAssocationEntry
    ) -> MatchedVariant:
        if len(entry.ref) > 50 or len(entry.alt) > 50:
            # structural variant, need to get the primary key
            # so need to have this use the mixin? if it exists for
            # variant annotators
            pass
            # variant_key = generated_pk
        else:

            variant_key = (
                entry.position,
                entry.ref,
                entry.alt,
            )
            db_record = reference_variants.get(variant_key)
            if db_record is None:
                # if SNV switch alleles and try again (trust INDEL directions)
                # theoretically this should never be needed because hipFG
                # standardized data is aligned to the reference genome
                # but there could be a dbSNP mismatch
                if len(entry.ref) == len(entry.alt) == 1:
                    variant_key = (
                        entry.position,
                        entry.alt,
                        entry.ref,
                    )
                db_record = reference_variants.get(variant_key)

        return db_record

    async def load(self, session, entries: list[GWASAssocationEntry]):
        embedded_track_records = self._embed_track_records([self._track_record])
        tracks: list[Track] = await self._load_track_records(embedded_track_records)

        track_id: int = tracks[0].track_id

        for chromosome, chromosome_group in groupby(
            entries, key=attrgetter("chromosome")
        ):
            if self._current_chromosome != chromosome:
                self._current_chromosome = chromosome
                self.logger.info(f"Loading associations on {self._current_chromosome}")

            chromosome_entries = list(chromosome_group)
            lookup_blocks = self._get_lookup_blocks(chromosome_entries, max_span=100000)

            associations = []
            for block in lookup_blocks:
                reference_variants: VariantLookupMap = (
                    await self._retrieve_variants_in_span(session, block.region)
                )
                for entry in entries[block.start_idx : block.end_idx]:
                    matched_db_record: MatchedVariant = self._get_variant_db_record(
                        reference_variants, entry
                    )
                    if matched_db_record is None:  # novel variant
                        # need to load and in Variant.Variant and write to file to be annotated
                        variant_stable_id, variant_pk = await self._load_variant(
                            session, entry
                        )
                        entry.variant_id = variant_stable_id
                        print(
                            entry.to_delimited_text(),
                            file=self._unannotated_variant_vcf_fh,
                        )

                    else:  # matched
                        if not matched_db_record.is_annotated:
                            entry.variant_id = matched_db_record.unique_stable_id
                            print(
                                entry.to_delimited_text(),
                                file=self._unannotated_variant_vcf_fh,
                            )
                        variant_pk = matched_db_record.id

                    # build the association entry
                    associations.append(
                        VariantAssociation(
                            track_id=track_id,
                            variant_id=variant_pk,
                            variant_stable_id=variant_stable_id,
                            neg_log10_pvalue=entry.neg_log10_pvalue,
                            pvalue=entry.pvalue,
                            effect_direction=entry.effect_direction,
                            test_allele=entry.test_allele,
                            run_id=self.run_id,
                        )
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
