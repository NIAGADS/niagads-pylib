from typing import Optional, TypeAlias

from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.genome_reference.human import HumanGenome
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class VariantLookupBlock(BaseModel):
    """Range indices and genomic region for a variant lookup subset."""

    start_idx: int
    end_idx: int
    region: OneBasedGenomicRegion


class MatchedVariant(BaseModel):
    """Basic identifying information for matched variant record"""

    id: int
    unique_stable_id: str  # 'NIAGADS_ID - chr:pos:ref:alt or SV id'
    is_adsp_variant: Optional[bool] = None
    is_annotated: Optional[bool] = None


VariantLookupKey: TypeAlias = str | tuple[int, str, str]
VariantLookupMap: TypeAlias = dict[VariantLookupKey, MatchedVariant]


class VariantLookupMixin:
    def __get_position(self, record):
        """Extract position from record that has either 'pos' or 'position' attribute."""
        if hasattr(record, "pos"):
            return record.pos
        elif hasattr(record, "position"):
            return record.position
        else:
            raise AttributeError(
                f"Record does not have 'pos' or 'position' attribute: {type(record)}"
            )

    def __get_chromosome(self, record):
        """Extract chromosome from record that has either 'chrom' or 'chromosome' attribute."""
        if hasattr(record, "chrom"):
            return record.chrom
        elif hasattr(record, "chromosome"):
            return record.chromosome
        else:
            raise AttributeError(
                f"Record does not have 'chrom' or 'chromosome' attribute: {type(record)}"
            )

    def _get_lookup_region(self, record: list):
        min_position = min(record, key=lambda entry: self.__get_position(entry))
        min_position = self.__get_position(min_position)
        max_position = max(record, key=lambda entry: self.__get_position(entry))
        max_position = self.__get_position(max_position)
        chromosome = self.__get_chromosome(record[0])

        return OneBasedGenomicRegion(
            start=min_position,
            end=max_position,
            chromosome=HumanGenome(chromosome),
        )

    def _get_lookup_blocks(
        self, records, max_span: int = 100000
    ) -> list[VariantLookupBlock]:
        """Define lookup subsets by recursively subdividing at position gaps.

        Recursively subdivides records by the largest gap in position until all
        resulting spans are within the max_span threshold. Returns index ranges
        with calculated genomic regions for efficient database lookups.

        Args:
            records: List of variant records with position attributes.
            max_span: Maximum allowed genomic span for a lookup. Defaults to 100000.

        Returns:
            List of LookupSubset objects containing start_idx, end_idx, and region.
        """
        lookup_range: OneBasedGenomicRegion = self._get_lookup_region(records)

        if (lookup_range.end - lookup_range.start) <= max_span:
            return [
                VariantLookupBlock(
                    start_idx=0, end_idx=len(records), region=lookup_range
                )
            ]

        # find largest gap
        positions = [self.__get_position(r) for r in records]
        gap_idx = (
            max(
                range(len(positions) - 1),
                key=lambda i: positions[i + 1] - positions[i],
            )
            + 1
        )

        # recursively subdivide each half
        left_ranges = self._get_lookup_blocks(records[:gap_idx], max_span)
        right_ranges = self._get_lookup_blocks(records[gap_idx:], max_span)

        # adjust right_ranges indices
        adjusted_right = [
            VariantLookupBlock(
                start_idx=r.start_idx + gap_idx,
                end_idx=r.end_idx + gap_idx,
                region=r.region,
            )
            for r in right_ranges
        ]
        return left_ranges + adjusted_right

    async def _retrieve_variants_in_span(
        self, session: AsyncSession, region: OneBasedGenomicRegion
    ) -> VariantLookupMap:
        """Retrieve variants within a genomic region.

        Standard variants are keyed by position, reference allele, and
        alternate allele. Structural variants are keyed by their unique
        NIAGADS identifier because their alternate allele may be null.

        Args:
            session (AsyncSession): Active asynchronous database session.
            region (OneBasedGenomicRegion): Genomic region used to constrain
                the lookup.

        Returns:
            dict: Mapping of variant lookup keys to database metadata. Standard
                variants use a ``(position, ref_allele, alt_allele)`` tuple;
                structural variants use their ``niagads_id`` (CHRM_SVTYPE_SEQHASH).
        """

        stmt = select(
            Variant.variant_id,
            Variant.niagads_id,
            Variant.position,
            Variant.ref_allele,
            Variant.alt_allele,
            Variant.is_adsp_variant,
            Variant.is_annotated,
            Variant.is_structural_variant,
        ).where(
            Variant.chromosome == str(region.chromosome),
            Variant.position.between(region.start, region.end),
        )
        result = (await session.execute(stmt)).all()

        return {
            (
                row.niagads_id
                if row.is_structural_variant
                else (row.position, row.ref_allele, row.alt_allele)
            ): MatchedVariant(
                id=row.variant_id,
                unique_stable_id=row.niagads_id,
                is_adsp_variant=row.is_adsp_variant,
                is_annotated=row.is_annotated,
            )
            for row in result
        }
