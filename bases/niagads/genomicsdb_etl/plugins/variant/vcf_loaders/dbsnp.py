"""
VCF File Loader ETL Plugin

Loads variants from VCF file into variant table.
Uses cyvcf2 for fast parsing.
Handles multiallelic variants by exploding them into separate records.
"""

from typing import Optional


from niagads.common.types import ETLOperation
from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.variant.variant import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import ResumeCheckpoint
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.ga4gh.annotators import GA4GHVRSService
from niagads.ga4gh.types import VariantNomenclature
from niagads.genome_reference.human import HumanGenome
from niagads.genomicsdb_etl.plugins.variant.vcf_loaders.base import (
    BaseVCFLoader,
    BaseVCFLoaderParams,
)
from niagads.vcf.types import VCFEntry
from sqlalchemy.ext.asyncio import AsyncSession

metadata = PluginMetadata(
    version="1.0",
    description="Load variants from VCF file into variant table",
    affected_tables=[Variant],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=True,
    parameter_model=BaseVCFLoaderParams,
)


@PluginRegistry.register(metadata)
class DBSnpVCFLoader(BaseVCFLoader):

    def transform(self, entry: VCFEntry) -> Optional[Variant]:
        """Transform VCF variant to Variant ORM object."""

        record: VariantRecord = self._generate_variant_identifier_record(
            entry, require_validation=False  # trust dbSNP
        )

        # TODO: extract ALFA frequencies from INFO
        allele_freq = None

        chromosome = HumanGenome(entry.chromosome)
        bin_index = self._find_bin_index(
            str(chromosome), record.span.start, record.span.end
        )

        return Variant(
            chromosome=chromosome,
            bin_index=bin_index,
            position=record.position,
            span=record.span,
            length=record.length,
            ref_allele=record.ref,
            alt_allele=record.alt,
            variant_class=str(record.variant_class),
            positional_id=record.positional_id,
            normalized_positional_id=record.normalized_positional_id,
            ref_snp_id=record.ref_snp_id,
            ga4gh_vrs=record.ga4gh_vrs.model_dump(),
            is_structural_variant=record.variant_class.is_structural_variant(),
            allele_frequency=allele_freq,
            run_id=self.run_id,
            external_database_release_id=self.external_database_id,
        )

    async def load(
        self, session: AsyncSession, records: list[Variant]
    ) -> Optional[ResumeCheckpoint]:
        if not records:
            return None
        await Variant.submit_many(session, records)
        return self.create_checkpoint(record=records[-1])
