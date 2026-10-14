from bisect import bisect_right

from niagads.common.models.types import Range
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from sqlalchemy import func, select


class BinIndexReferenceMixin:
    """mixin allowing multi-task feature loading plugins (e.g., tracks) to
    leverage the bin_index without introducing class inheritence conflicts.

    Requires existence of `_bin_index_reference` class member:
    ```python
        self._bin_index_reference: dict = defaultdict(
            lambda: defaultdict(lambda: {"starts": [], "bins": []})
        )
    ```

    Suggest calling `_fetch_bin_index_mapping` during `on_run_start`

    """

    def __has_bin_index_reference(self):
        """runtime error to ensure developers create the class member"""
        if not hasattr(self, "_bin_index_reference"):
            raise RuntimeError(
                "Class member `self._bin_index_reference` not initialized.  See `BaseFeatureLoader` for example."
            )

    async def _fetch_bin_index_mapping(self, session):
        """Load the interval-bin lookup table into memory.

        Args:
            session (AsyncSession): SQLAlchemy async session used to fetch interval-bin
                records.

        Raises:
            RuntimeError: If the bin index reference has not been initialized.
        """
        self.__has_bin_index_reference()
        self.logger.info("Fetching Bin Index Reference Mapping")

        stmt = select(IntervalBin).order_by(
            IntervalBin.chromosome,
            IntervalBin.bin_level.desc(),
            func.lower(IntervalBin.span),
        )

        result = (await session.execute(stmt)).scalars().all()

        bin: IntervalBin
        for bin in result:
            self._bin_index_reference[bin.chromosome][bin.bin_level]["starts"].append(
                bin.span.start
            )
            self._bin_index_reference[bin.chromosome][bin.bin_level]["bins"].append(
                (bin.span.end, bin.bin_index)
            )

    def _find_bin_index(self, chromosome, span: Range):
        """Return the bin index that encloses the given genomic span.

        Args:
            chromosome (str): Chromosome key for the lookup table.
            span (Range): Genomic range to map to the smallest enclosing bin.

        Returns:
            int | None: The enclosing bin index, or None if no bin contains the span.

        Raises:
            RuntimeError: If the bin index reference has not been initialized.
        """
        self.__has_bin_index_reference()
        for level in self._bin_index_reference[chromosome]:
            starts = self._bin_index_reference[chromosome][level]["starts"]
            bins = self._bin_index_reference[chromosome][level]["bins"]

            split_index = bisect_right(starts, span.start) - 1
            if split_index >= 0:
                bin_end, bin_index = bins[split_index]
                if span.end < bin_end:
                    return bin_index
