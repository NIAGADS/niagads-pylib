from bisect import bisect_right
from collections import defaultdict
from typing import Any, Dict, Optional
from niagads.common.models.types import Range
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from sqlalchemy import func, select


class BaseFeatureLoaderParams(BasePluginParams, ExternalDatabaseRefMixin):
    pass


class BaseFeatureLoaderPlugin(AbstractBasePlugin):
    """
    Foundational class for plugins loading genomic features.

    Overloads `on_run_start` to handle the external database referencel lookup
    and retrieve IntervalBin reference from database into memory.

    Provides helper function `find_bin_index` to find the minimum
    enclosing bin for the sequence feature to enable indexing.
    """

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        self.__external_database: ExternalDatabase = None
        # bin index reference; fetched into memory
        self.__bin_index_reference: dict = defaultdict(
            lambda: defaultdict(lambda: {"starts": [], "bins": []})
        )

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def __fetch_bin_index_map(self, session):
        stmt = select(IntervalBin).order_by(
            IntervalBin.chromosome,
            IntervalBin.bin_level.desc(),
            func.lower(IntervalBin.span),
        )

        result = (await session.execute(stmt)).scalars().all()

        bin: IntervalBin
        for bin in result:
            self.__bin_index_reference[bin.chromosome][bin.bin_level]["starts"].append(
                bin.span.start
            )
            self.__bin_index_reference[bin.chromosome][bin.bin_level]["bins"].append(
                (bin.span.end, bin.bin_index)
            )

    async def on_run_start(self, session):
        if self.is_etl_run:
            # validate the xdbref against the database
            self.__external_database = await self._params.fetch_xdbref(session)

            # fetch bin index reference
            await self.__fetch_bin_index_map(session)

    def _find_bin_index(self, chromosome, span: Range):
        for level in self.__bin_index_reference[chromosome]:
            starts = self.__bin_index_reference[chromosome][level]["starts"]
            bins = self.__bin_index_reference[chromosome][level]["bins"]

            split_index = bisect_right(starts, span.start) - 1
            if split_index >= 0:
                bin_end, bin_index = bins[split_index]
                if span.end < bin_end:
                    return bin_index
