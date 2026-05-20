"""
DBSNP File Loader ETL Plugin

Loads DBSNP variants from VCF file into variant table.
- calculates GA4GH VRS
- extracts ALFA frequencies
**ASSUMES EMPTY TABLE**
"""

import asyncio
from time import perf_counter
from typing import Iterator, Optional
from niagads.utils.logging import async_timed

import cyvcf2
from niagads.common.types import ETLOperation
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import ResumeCheckpoint
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy

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


class ALFAAnnotatedVariantRecord(VariantRecord):
    allele_frequency: Optional[dict] = None


@PluginRegistry.register(metadata)
class dbSNPVCFLoader(BaseVCFLoader):

    def __init__(
        self,
        params: BaseVCFLoaderParams,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._skip_normalization = False

    def __parse_allele_frequencies(self, freq_str: str, allele_index: int):

        def get_value(values):
            try:
                freq_value = values[allele_index]
                return None if freq_value == "." else float(freq_value)
            except IndexError:
                return None

        frequencies = {}
        for population_frequencies in freq_str.split("|"):
            pop, pop_freq_str = population_frequencies.split(":")
            pop_allele_freq = get_value(pop_freq_str.split(","))
            if pop_allele_freq is not None:
                frequencies[pop] = pop_allele_freq

        return frequencies

    def extract(self) -> Iterator[list[VCFEntry]]:
        """Extract variants from VCF in seqrepo_batch_size batches."""
        reader = cyvcf2.Reader(self._params.file)
        try:
            for entry in reader:
                # index starts at 1 b/c ref is 0 in lists in INFO annotations
                for allele_index, alt in enumerate(entry.ALT, start=1):
                    vcf_entry = VCFEntry.from_cyvcf2_variant(entry, alt_allele=alt)
                    if "FREQ" in vcf_entry.info:  # ALFA frequencies
                        vcf_entry.info["FREQ"] = self.__parse_allele_frequencies(
                            vcf_entry.info["FREQ"], allele_index
                        )
                    else:
                        vcf_entry.info["FREQ"] = None

                    yield vcf_entry

        finally:
            reader.close()

    async def transform(self, entry: VCFEntry) -> ALFAAnnotatedVariantRecord:
        """Transform VCF variant to Variant record (with standardized IDs)."""

        variant_record = self._generate_variant_identifier_record(
            entry, require_validation=False  # trust dbSNP
        )
        if variant_record is None:
            return None

        return ALFAAnnotatedVariantRecord(
            **variant_record.model_dump(), allele_frequency=entry.info["FREQ"]
        )

    def __is_duplicate(self, variant: ALFAAnnotatedVariantRecord):
        """
        Checks if the given variant is a duplicate within the current bin.

        Since variants in different bins cannot overlap in position and all "niagads_id" (stable, unique ids)
        are based on position it is sufficient to check for duplicates only within the current bin.
        This approach avoids the need to track all seen variants genome-wide, which would be infeasible for large datasets.

        current_bin and current_bin_variants are class members b/c a bin may persist across a chunked load
        """
        if self._current_bin_index is not None:
            if variant.id in self._current_bin_variants:
                return True

    async def load(
        self, session: AsyncSession, records: list[ALFAAnnotatedVariantRecord]
    ) -> Optional[ResumeCheckpoint]:

        variants = []
        for record in records:
            if record is None:
                self.inc_tx_count(Variant, ETLOperation.SKIP)  # invalid variant
                continue
            if self.__is_duplicate(record):
                if self._verbose:
                    self.logger.warning(
                        f"Skipping Duplicate Variant: NIAGADS_ID = {record.id}; RECORD = {record.positional_id} / {record.ref_snp_id} / DUPLICATES {self._current_bin_variants[record.id]}"
                    )
                self.inc_tx_count(Variant, ETLOperation.SKIP)
                continue

            variant = Variant.from_variant_record(record)
            variant.allele_frequency = record.allele_frequency
            variant.run_id = self.run_id
            variant.bin_index = self._find_bin_index(
                str(record.chromosome), record.span
            )
            variant.external_database_id = self.external_database_id
            variants.append(variant)

            if variant.bin_index != self._current_bin_index:
                self._current_bin_index = variant.bin_index
                self._current_bin_variants = {}
            self._current_bin_variants[record.id] = record.ref_snp_id

        # as long as batches are small this is faster than copy
        await Variant.submit_many(session, variants)

        return self.create_checkpoint(record=records[-1])
