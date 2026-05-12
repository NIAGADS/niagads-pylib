"""
DBSNP File Loader ETL Plugin

Loads DBSNP variants from VCF file into variant table.
- calculates GA4GH VRS
- extracts ALFA frequencies
**ASSUMES EMPTY TABLE**
"""

from typing import Iterator, Optional


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


class dbSNPRecord(VariantRecord):
    allele_frequency: Optional[dict] = None


@PluginRegistry.register(metadata)
class dbSNPVCFLoader(BaseVCFLoader):

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

    def extract(self) -> Iterator[VCFEntry]:
        """Extract variants from VCF."""
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

    def transform(self, entry: VCFEntry) -> Optional[dbSNPRecord]:
        """Transform VCF variant to Variant ORM object."""

        record: dbSNPRecord = dbSNPRecord(
            **self._generate_variant_identifier_record(
                entry, require_validation=False  # trust dbSNP
            ).model_dump()
        )

        record.allele_frequency = entry.info["FREQ"]
        return record

    def __is_duplicate(self, variant: dbSNPRecord):
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
        self, session: AsyncSession, records: list[dbSNPRecord]
    ) -> Optional[ResumeCheckpoint]:
        variants = []

        for record in records:
            if self.__is_duplicate(record):
                self.logger.warning(
                    f"Skipping Duplicate Variant: NIAGADS_ID = {record.id}; RECORD = {record}"
                )
                self.inc_tx_count(Variant, ETLOperation.INSERT)
                continue

            self.logger.debug(f"{record} - {record.variant_class}")
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
            self._current_bin_variants[record.id] = True

        await Variant.submit_many(session, variants)
        return self.create_checkpoint(record=records[-1])
