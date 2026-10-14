from collections import defaultdict
from typing import Any, Dict, Optional

from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.genomicsdb_etl.plugins.common.mixins.intervals import (
    BinIndexReferenceMixin,
)
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefParamMixin,
)


class BaseFeatureLoaderParams(BasePluginParams, ExternalDatabaseRefParamMixin):
    pass


class BaseFeatureLoaderPlugin(AbstractBasePlugin, BinIndexReferenceMixin):
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
        self._bin_index_reference: dict = defaultdict(
            lambda: defaultdict(lambda: {"starts": [], "bins": []})
        )

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        if self.is_etl_run:
            # validate the xdbref against the database
            self.__external_database = await self._params.fetch_xdbref(session)

            # fetch bin index reference
            self._bin_index_reference = await self._fetch_bin_index_mapping(session)
