from typing import Dict, Iterator, Optional
import cyvcf2
from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.models.record import VariantIdentifier, VariantRecord
from niagads.common.variant.types import VariantClass
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.parameters import EnvVariableMixin, PathValidatorMixin
from niagads.ga4gh.annotators import PrimaryKeyGenerator
from niagads.genome_reference.human import GenomeBuild
from niagads.genomicsdb_etl.plugins.common.bases.features import (
    BaseFeatureLoaderParams,
    BaseFeatureLoaderPlugin,
)
from niagads.vcf.types import VCFEntry
from pydantic import Field


class BaseVCFLoaderParams(
    BaseFeatureLoaderParams, PathValidatorMixin, EnvVariableMixin
):
    file: str = Field(..., description="Full path to VCF file")

    genome_build: Optional[GenomeBuild] = Field(
        default=GenomeBuild.GRCh38,
        description=f"Reference genome build, one of {GenomeBuild.list()}",
    )

    seqrepo_data_proxy: Optional[str] = Field(
        default=None,
        description="URL to seqrepo service or full path to seqrepo cache for GA4GH VRS",
    )

    skip_ga4gh_vrs: Optional[bool] = Field(
        defualt=False,
        description="Skip generating GA4GH VRS representation; note: GA4GH VRS calls with still be made to generate SV stable IDs",
    )

    seqrepo_lru_cache_maxsize: Optional[str] = Field(
        default="none",
        description="Maximum number of SeqRepo lookup results kept in the in-memory LRU cache. Use an integer or 'none' for unlimited.",
    )
    seqrepo_fd_cache_maxsize: Optional[int] = Field(
        default=100,
        description="Maximum number of sequence file handles SeqRepo keeps open. Higher values reduce repeated file open/close overhead.",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


class BaseVCFLoader(BaseFeatureLoaderPlugin):
    _params: BaseVCFLoaderParams

    def __init__(
        self,
        params: BaseVCFLoaderParams,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._pk_generator: Optional[PrimaryKeyGenerator] = None

        # for avoiding record duplications w/out creating a unique constraint
        self._current_bin_variants: Dict[str, bool] = {}
        self._current_bin_index: str = None
        self._skip_normalization: bool = False

    async def on_run_start(self, session):
        await super().on_run_start(session)
        self._pk_generator = PrimaryKeyGenerator(
            genome_build=self._params.genome_build,
            seqrepo_data_proxy=self._params.seqrepo_data_proxy,
            logger=self.logger if self._verbose else None,
        )

    def extract(self) -> Iterator[VCFEntry]:
        """Extract variants from VCF."""
        reader = cyvcf2.Reader(self._params.file)
        try:
            for entry in reader:
                for alt in entry.ALT:
                    yield VCFEntry.from_cyvcf2_variant(entry, alt_allele=alt)

        finally:
            reader.close()

    def _generate_variant_identifier_record(
        self, entry: VCFEntry, require_validation: bool = True
    ):
        positional_id = f"{entry.chrom.value}:{entry.pos}:{entry.ref}:{entry.alt}"
        try:
            record: VariantRecord = VariantRecord.from_positional_id(positional_id)
        except Exception as err:
            if "String should match pattern" in str(err):
                self.logger.debug(f"Invalid allele string: {positional_id}")
                return None
            raise

        entry_id = entry.id.lower()
        record.ref_snp_id = entry_id if entry_id.startswith("rs") else None

        # generate the GA4GH VRS allele
        ga4gh_allele = self._pk_generator.ga4gh_service.variant_to_vrs_allele(
            record,
            normalize=not self._skip_normalization,
            require_validation=require_validation,
            as_json=False,
        )

        record.ga4gh_vrs = Allele(**ga4gh_allele.model_dump(exclude_none=True))
        self._pk_generator.set_primary_key(record, require_validation=False)
        # if a short indel use the normalized GA4GH VRS allele to generate the normalized positional id
        if (
            not self._skip_normalization
            and not record.variant_class == VariantClass.SNV
        ):
            if record.ref is not None and record.alt is not None:
                record.normalized_positional_id = (
                    self._pk_generator.ga4gh_service.fast_normalize_variant(
                        record.positional_id
                    )
                )
        else:
            record.normalized_positional_id = record.id

        if self._verbose:
            self.logger.debug(f"{record.id} | {record.model_dump(exclude_none=True)}")

        if len(record.id) > 150:
            self.logger.critical(
                f"Invalid Stable ID Generated - {record.id}: {record.model_dump()}"
            )

        return record
