from niagads.common.core import ComponentBaseMixin
from niagads.common.models.types import Range
from niagads.database.genomicsdb.intervals import (
    fetch_bin_index_reference,
    find_bin_index,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import Ltree


class BinIndexReferenceMixin(ComponentBaseMixin):
    """Provide interval-bin lookups for feature-loading plugins.

    Call _fetch_bin_index_mapping during on_run_start before looking up bins.
    """

    async def _fetch_bin_index_mapping(self, session: AsyncSession) -> None:
        """Load and retain the interval-bin reference for the current ETL run.

        Args:
            session (AsyncSession): Database session used to fetch interval bins.
        """
        self.logger.info("Fetching Bin Index Reference Mapping")
        self._bin_index_reference = await fetch_bin_index_reference(session)

    def _find_bin_index(self, chromosome: str, span: Range) -> Ltree | None:
        """Return the smallest enclosing bin from the loaded reference.

        Args:
            chromosome (str): Chromosome key in the reference mapping.
            span (Range): Genomic span whose start must be within a bin and whose
                end must be strictly less than the bin's end coordinate.

        Returns:
            Ltree | None: Index of the smallest enclosing bin, or None if no bin
                contains the span.

        Raises:
            RuntimeError: If the bin index reference has not been loaded.
        """
        if not hasattr(self, "_bin_index_reference"):
            raise RuntimeError("Bin index reference has not been loaded.")
        return find_bin_index(self._bin_index_reference, chromosome, span)
