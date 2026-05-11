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

        return {
            k: freq
            for pair in freq_str.split("|")
            for k, v in [pair.split(":", 1)]
            for freq in [get_value(v.split(","))]
            if freq is not None
        }

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

        record: dbSNPRecord = self._generate_variant_identifier_record(
            entry, require_validation=False  # trust dbSNP
        )

        # TODO: extract ALFA frequencies from INFO
        record.allele_frequency = None

    async def load(
        self, session: AsyncSession, records: list[dbSNPRecord]
    ) -> Optional[ResumeCheckpoint]:
        variants = []
        for record in records:
            variant = Variant.from_variant_record(record)
            variant.allele_frequency = record.allele_frequency
            variant.run_id = self.run_id
            variant.bin_index = self._find_bin_index(
                str(record.chromosome), record.span.start, record.span.end
            )
            variant.external_database_id = self.external_database_id
            variants.append(variant)

        await Variant.submit_many(session, variants)
        return self.create_checkpoint(record=records[-1])
