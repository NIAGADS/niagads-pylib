"""
dbSNP RefSNP Merge History Loader Plugin
- Loads RefSNP merge history into the Variant.RefSnpAlias table.
"""

import json
from typing import Any, Dict, Iterator, List, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.variant.mappings import RefSNPAlias
from niagads.database.genomicsdb.schema.variant.types import RefSNPMergeHistory
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.sys import read_open_ctx
from pydantic import Field, field_validator


class MergeRecord(RefSNPMergeHistory):
    ref_snp_id: str = Field(alias="merged_rsid")
    merge_history: Optional[list[RefSNPMergeHistory]] = None

    @field_validator("ref_snp_id", mode="before")
    def prefix_ref_snp_id(cls, value: str):
        return cls._prefix_ref_snp_id(value)


class RefSNPMergeHistoryLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for DBSnpMergeHistoryLoader plugin."""

    file: str = Field(..., description="full path to dbSNP merge history JSON file")

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        f"ETL Plugin to load dbSNP merge history from a JSON file into {RefSNPAlias.table_name()}. "
        f"Creates mappings showing which rsids were merged into target rsids."
    ),
    affected_tables=[RefSNPAlias],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=RefSNPMergeHistoryLoaderParams,
)


@PluginRegistry.register(metadata)
class RefSNPMergeHistory(AbstractBasePlugin):
    """
    ETL plugin for loading dbSNP RefSNP merge history file into RefSnpAlias.
    """

    _params: RefSNPMergeHistoryLoaderParams

    def __init__(
        self,
        params,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        # for avoiding record duplications w/out creating a unique constraint
        self.__external_database: ExternalDatabase = None

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        """Validate xdbref against the database and fetch external database record."""
        if self.is_etl_run:
            self.__external_database = await self._params.fetch_xdbref(session)

    def extract(self) -> Iterator[Dict[str, Any]]:
        """
        Extract dbSNP merge history records from JSON file.

        Each line is a JSON object containing merge history data.

        Yields:
            Iterator[Dict]: Dictionary containing merge history record data.
        """
        with read_open_ctx(self._params.file) as fh:
            entry_count = 0
            for line in fh:
                entry = json.loads(line.strip())
                snapshot = entry.get("merged_snapshot_data")
                if snapshot["merged_into"]:  # no further merges
                    entry_count += 1
                    yield entry

            self.logger.info(f"Extracted {entry_count} entries.")

    def transform(self, entry: dict) -> MergeRecord:
        """
        Transform a dbSNP merge history record into intermediate data objects.
        """

        ref_snp_id = entry["refsnp_id"]
        merge_history = []
        for merge_entry in entry.get("dbsnp1_merges", []):
            merge_history.append(MergeRecord(merged_into=ref_snp_id, **merge_entry))

        snapshot = entry.get("merged_snapshot_data")
        record = MergeRecord(
            ref_snp_id=ref_snp_id,
            merged_into=snapshot["merged_into"][0],
            merge_build=snapshot["proxy_build_id"],
            merge_date=snapshot["proxy_time"],
        )
        if merge_history:
            record.merge_history = merge_history
        return record

    def get_record_id(self, record: MergeRecord) -> str:
        """
        Extract unique identifier from a MergeAliasRecord.

        Args:
            record: MergeAliasRecord object.

        Returns:
            str: Unique identifier combining ref_snp_id and merged_into.
        """
        return f"{record.ref_snp_id} -> {record.merged_into}"

    async def load(self, session, records: List[MergeRecord]):
        """
        Insert RefSnpAlias records into the database.
        """
        aliases = []
        for alias_record in records:
            # Create RefSnpAlias ORM object with database-dependent fields
            aliases.append(
                RefSNPAlias(
                    **alias_record.model_dump(),
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
            )

        await RefSNPAlias.submit_many(session, aliases)
        return self.create_checkpoint(record=records[-1])
