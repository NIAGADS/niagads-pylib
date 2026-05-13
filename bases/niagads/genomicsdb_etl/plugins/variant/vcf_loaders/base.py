from typing import Dict, Iterator, Optional
import cyvcf2
from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.models.record import VariantRecord
from niagads.common.variant.types import VariantClass
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.ga4gh.annotators import PrimaryKeyGenerator
from niagads.genome_reference.human import GenomeBuild
from niagads.genomicsdb_etl.plugins.common.bases.features import (
    BaseFeatureLoaderParams,
    BaseFeatureLoaderPlugin,
)
from niagads.vcf.types import VCFEntry
from pydantic import Field


class BaseVCFLoaderParams(BaseFeatureLoaderParams, PathValidatorMixin):
    file: str = Field(..., description="Full path to VCF file")

    genome_build: Optional[GenomeBuild] = Field(
        default=GenomeBuild.GRCh38,
        description=f"Reference genome build, one of {GenomeBuild.list()}",
    )

    seqrepo_service_url: Optional[str] = Field(
        default="http://localhost:5000/seqrepo",
        description="URL to seqrepo service for GA4GH VRS",
    )

    seqrepo_batch_size: Optional[int] = Field(
        default=50,
        description="number of parallel requests to seqrepo service for GA4GH VRS and stable ID Generation",
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
            seqrepo_service_url=self._params.seqrepo_service_url,
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

    def get_record_id(self, record: Variant) -> str:
        return record.id

    def _generate_variant_identifier_record(
        self, entry: VCFEntry, require_validation: bool = True
    ):
        positional_id = f"{entry.chrom}:{entry.pos}:{entry.ref}:{entry.alt}"
        record: VariantRecord = VariantRecord.from_positional_id(positional_id)
        record.ref_snp_id = (
            entry.id.lower() if entry.id.lower().startswith("rs") else None
        )

        # generate the GA4GH VRS allele
        ga4gh_allele = self._pk_generator.ga4gh_service.variant_to_vrs_allele(
            record,
            normalize=not self._skip_normalization,
            require_validation=require_validation,
            as_json=False,
        )

        # if a short indel use the normalized GA4GH VRS allele to generate the normalized positional id
        if not self._skip_normalization and record.variant_class.is_short_indel():
            try:
                record.normalized_positional_id = (
                    self._pk_generator.ga4gh_service.allele_to_positional_variant(
                        ga4gh_allele
                    )
                )
            except:  # most likely a repeat so the normalized sequence is longer than expected
                pass

        if self._verbose:
            self.logger.debug(
                f"{positional_id} | {record.variant_class} | {ga4gh_allele.model_dump(exclude_none=True)}"
            )

        record.ga4gh_vrs = Allele(**ga4gh_allele.model_dump(exclude_none=True))
        # FIXME: need to indicate if variant is already normalized for pk generator as well
        # need to test that if we don't normalize here we still get the right variant back
        self._pk_generator.set_primary_key(record, require_validation=False)

        return record
