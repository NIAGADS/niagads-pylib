from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.genome_reference.human import HumanGenome
from niagads.vcf.types import VCFEntry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class VariantLookupMixin:
    def _get_lookup_region(self, entries: list[VCFEntry]):
        min_position = min(entries, key=lambda entry: entry.pos).pos
        max_position = max(entries, key=lambda entry: entry.pos).pos
        return OneBasedGenomicRegion(start=min_position, end=max_position, chromosome=HumanGenome(entries[0].chrom))

    async def _retrieve_variants_in_span(self, session: AsyncSession, region: OneBasedGenomicRegion):
        """
        Retrieve all variants in the specified genomic region
    
        Args:
            session (AsyncSession): session
            entries (list[VCFEntry]): list of vcf entries
        """

        stmt = (
            select(
                Variant.variant_id,
                Variant.position,
                Variant.ref_allele,
                Variant.alt_allele,
            )
            .where(
                Variant.chromosome == str(region.chromosome),
                Variant.position.between(region.start, region.end),
            )
        )
        result = (await session.execute(stmt)).all()
        return {
            (row.position, row.ref_allele, row.alt_allele): row.variant_id
            for row in result
        }