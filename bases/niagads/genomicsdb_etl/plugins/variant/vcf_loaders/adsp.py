from typing import Optional

from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.common.types import ETLOperation
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genome_reference.human import HumanGenome
from niagads.genomicsdb_etl.plugins.variant.base import VariantLookupMixin
from niagads.genomicsdb_etl.plugins.variant.vcf_loaders.base import (
    BaseVCFLoader,
    BaseVCFLoaderParams,
)
from niagads.utils.list import chunker
from niagads.utils.sys import timer
from niagads.vcf.types import VCFEntry
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class ADSPVCFLoaderParams(BaseVCFLoaderParams):
    insert_only: Optional[bool] = Field(
        default=False,
        description="Insert novel variants only; skip flagging existing variants as is_adsp_variant",
    )


metadata = PluginMetadata(
    version="1.0",
    description="Load variants from VCF file into variant table",
    affected_tables=[Variant],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.LOAD,
    is_large_dataset=True,
    parameter_model=ADSPVCFLoaderParams,
    can_resume=True,  # TODO: implement resume
)


"""
Expected file format.  
Note pipeline as of 06-2026: every variant in the file is a 'PASS'.  
INFO field only stores count, frequency info, so no QC loaded for GenomicsDB anymore

#CHROM  POS     ID      REF     ALT     QUAL    FILTER  INFO    FORMAT
chr8    72569326        chr8_72569326_C_T       C       T       1647    .       AF=0.00210267;AQ=1647;AC=246;AN=116994  GT
chr8    72569327        chr8_72569327_G_A;chr8_72569327_G_C     G       A,C     1470    .       AF=0.004077,3.4e-05;AQ=1470,806;AC=477,4;AN=116994      GT
chr8    72569329        chr8_72569329_G_C;chr8_72569329_G_T;chr8_72569329_GA_G  GA      CA,TA,G 781     .       AF=1.7e-05,1.7e-05,9e-06;AQ=781,718,277;AC=2,2,1;AN=116990      GT
"""


@PluginRegistry.register(metadata)
class ADSPVCFLoader(BaseVCFLoader, VariantLookupMixin):
    _params: ADSPVCFLoaderParams

    async def transform(self, entry: VCFEntry):
        return entry

    async def load(self, session: AsyncSession, entries: list[VCFEntry]):
        # iterate over the entries finding matching variant or variants in case of multi-allelic entries
        # update matches to set is_adsp_variant to true
        # for missing (new variants), use parent functions to generate primary keys/GA4GH VRS and insert
        # lookup against DB
        lookup_region = self._get_lookup_region(entries)
        self.logger.debug(f"Lookup Region: {str(lookup_region)}")
        async with timer("Fetch variants in span", logger=self.logger):
            reference_variants = await self._retrieve_variants_in_span(
                session, lookup_region, incl_adsp_flag=True
            )

        update_variant_ids = []
        new_variants = []
        for entry in entries:
            variant_key = (entry.pos, entry.ref, entry.alt)
            db_record = reference_variants.get(variant_key)

            if db_record is None:
                # if SNV switch alleles and try again (trust INDEL directions)
                if len(entry.ref) == len(entry.alt) == 1:
                    variant_key = (entry.pos, entry.alt, entry.ref)
                    db_record = reference_variants.get(variant_key)

            if db_record is not None:
                if not self._params.insert_only and not db_record["is_adsp_variant"]:
                    update_variant_ids.append(db_record["id"])
                else:
                    self.inc_tx_count(Variant, ETLOperation.SKIP)

            else:
                variant_record = self._generate_variant_identifier_record(entry)
                if (
                    variant_record is None
                ):  # TODO: possibly log and skip; let's see if this occurs first
                    raise ValueError(
                        f"Unable to generate variant record for ADSP entry: {entry}"
                    )

                variant = Variant.from_variant_record(variant_record)
                variant.is_adsp_variant = True
                variant.run_id = self.run_id
                variant.bin_index = self._find_bin_index(
                    str(variant_record.chromosome), variant_record.span
                )
                variant.external_database_id = self.external_database_id
                new_variants.append(variant)

        if update_variant_ids:
            num_updateable_variants = len(update_variant_ids)
            self.logger.debug(
                f"Found {num_updateable_variants} existing variants to update"
            )
            async with timer("Bulk updates", logger=self.logger):
                # sqlalchemy asyncpg dialect limits number of args in a statement to 32,767
                chunks = chunker(update_variant_ids, 25000)
                for chunk in chunks:
                    stmt = (
                        update(Variant)
                        .where(Variant.variant_id.in_(chunk))
                        .values(is_adsp_variant=True)
                    )
                    result = await session.execute(stmt)
                    self.inc_tx_count(Variant, ETLOperation.UPDATE, result.rowcount)

        if new_variants:
            self.logger.debug(f"Found {len(new_variants)} novel variants - inserting")
            async with timer("Bulk inserts", logger=self.logger):
                await Variant.submit_many(session, new_variants)

        return self.create_checkpoint(record=entries[-1])

    def get_record_id(self, record: VCFEntry) -> str:
        return f"{record.chrom.value}:{record.pos}:{record.ref}:{record.alt}"
