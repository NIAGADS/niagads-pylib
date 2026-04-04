"""`IntervalBin` database model"""

from niagads.common.genomic.regions.models import GenomicRegion
from niagads.common.models.types import Range
from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.database.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.database.genomicsdb.schema.reference.genome import GenomeReference
from niagads.genome_reference.human import HumanGenome
from sqlalchemy import Integer, and_, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class IntervalBin(ReferenceTableBase, GenomicRegionMixin):
    __tablename__ = "intervalbin"
    _stable_id = "bin_index"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(ReferenceTableBase._schema, __tablename__),
        ReferenceTableBase.__table_args__,
    )

    interval_bin_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bin_level: Mapped[int] = mapped_column(Integer)

    @classmethod
    async def find_bin_index(
        cls, session: AsyncSession, chromosome: HumanGenome, span: Range
    ):
        """
        Find the most specific (deepest level) bin that contains the given genomic region.

        Handles programmatic flanking regions that may extend past chromosome boundaries
        by clamping coordinates to valid range [1, chrSize].

        Args:
            session (AsyncSession): SQLAlchemy async session for database access.
            region (GenomicRegion): The genomic region to bin.

        Returns:
            ltree or None: The bin_index (ltree) for the most specific bin containing the region,
                or None if no bin found.

        Raises:
            Exception: If chromosome is not found in genome reference.
        """
        # Get chromosome size
        chr_size_stmt = select(GenomeReference.chromosome_length).where(
            GenomeReference.chromosome == str(chromosome)
        )
        chr_size_result = await session.execute(chr_size_stmt)
        chr_size = chr_size_result.scalar()

        if chr_size is None:
            raise NoResultFound(f"Chromosome {chromosome} not found in GenomeReference")

        # Constrain end to valid bounds; handles flanking regions past chromosome boundaries
        end = min(span.end, chr_size - 1)

        # Create query range
        query_range = Range(start=span.start, end=end, inclusive_end=True)

        # Find the most specific (deepest level) bin containing the region
        bin_stmt = (
            select(IntervalBin.bin_index)
            .where(
                and_(
                    IntervalBin.chromosome == str(chromosome),
                    # The bin's genomic_region must contain the query range
                    IntervalBin.span.op("@>")(query_range),
                )
            )
            .order_by(
                # Order by bin_index depth (nlevel) descending to get the most specific
                func.nlevel(IntervalBin.bin_index).desc()
            )
            .limit(1)
        )

        result = await session.execute(bin_stmt)
        bin_index = result.scalar()
        if bin_index is None:
            raise NoResultFound(f"Unable to assign bin_index to region {region}")
        return bin_index
