"""Load and search GenomicsDB interval-bin references."""

from bisect import bisect_right
from collections import defaultdict

from niagads.common.models.types import Range
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import Ltree


async def fetch_bin_index_reference(session: AsyncSession) -> dict:
    """Load interval bins ordered by chromosome, deepest level, and start.

    Args:
        session (AsyncSession): Database session used to fetch interval bins.

    Returns:
        dict: Mapping keyed by chromosome and bin level, with sorted start
            coordinates and corresponding end-coordinate/bin-index pairs.
    """
    reference = defaultdict(lambda: defaultdict(lambda: {"starts": [], "bins": []}))
    stmt = select(IntervalBin).order_by(
        IntervalBin.chromosome,
        IntervalBin.bin_level.desc(),
        func.lower(IntervalBin.span),
    )
    result = (await session.execute(stmt)).scalars().all()

    for bin in result:
        level = reference[bin.chromosome][bin.bin_level]
        level["starts"].append(bin.span.start)
        level["bins"].append((bin.span.end, bin.bin_index))

    return reference


def find_bin_index(reference: dict, chromosome: str, span: Range) -> Ltree | None:
    """Return the smallest enclosing bin, or None if no bin contains the span.

    Args:
        reference (dict): Mapping returned by fetch_bin_index_reference.
        chromosome (str): Chromosome key in the reference mapping.
        span (Range): Genomic span whose start must be within a bin and whose
            end must be strictly less than the bin's end coordinate.

    Returns:
        Ltree | None: Index of the smallest enclosing bin, or None if no bin
            contains the span.
    """
    for level in reference[chromosome].values():
        split_index = bisect_right(level["starts"], span.start) - 1
        if split_index >= 0:
            bin_end, bin_index = level["bins"][split_index]
            if span.end < bin_end:
                return bin_index

    return None
