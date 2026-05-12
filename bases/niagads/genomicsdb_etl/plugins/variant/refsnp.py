"""
dbSNP RefSNP Merge History Loader Plugin
- Loads RefSNP merge history into the Variant.RefSnpAlias table.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.variant.mappers import RefSnpAlias
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from dateutil.parser import parse as parse_datetime


class Alias(BaseModel):
    merged_into: str
    ref_snp_id: str = Field(alias="merged_rsid")
    merge_build: int = Field(alias="revision")
    merge_date: str

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("merge_date", mode="before")
    def format_date(cls, value: str):
        return (
            parse_datetime(value)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )

    @classmethod
    def __prefix_ref_snp_id(cls, rsid: str):
        if rsid.startswith("rs"):
            return rsid
        else:
            return f"rs{rsid}"

    @field_validator("merged_into", mode="before")
    def prefix_merged_into(cls, value: str):
        return cls.__prefix_ref_snp_id(value)

    @field_validator("ref_snp_id", mode="before")
    def prefix_ref_snp_id(cls, value: str):
        return cls.__prefix_ref_snp_id(value)


class RefSNPMergeHistoryLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for DBSnpMergeHistoryLoader plugin."""

    file: str = Field(..., description="full path to dbSNP merge history JSON file")

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        f"ETL Plugin to load dbSNP merge history from a JSON file into {RefSnpAlias.table_name()}. "
        f"Creates mappings showing which rsids were merged into target rsids."
    ),
    affected_tables=[RefSnpAlias],
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
            for line_num, line in enumerate(fh, start=1):
                yield json.loads(line.strip())

            self.logger.info(f"Read {line_num} entries.")

    def transform(self, entry: dict) -> List[RefSnpAlias]:
        """
        Transform a dbSNP merge history record into intermediate data objects.
        """

        entry_id = entry["refsnp_id"]
        alias_records = []
        merge_history = entry.get("dbsnp1_merges", [])
        for merge_entry in merge_history:
            alias_records.append(Alias(merged_into=entry_id, **merge_entry))

        snapshot = entry.get("merged_snapshot_data")
        try:
            alias_records.append(
                Alias(
                    ref_snp_id=entry_id,
                    merged_into=snapshot["merged_into"][0],
                    merge_build=snapshot["proxy_build_id"],
                    merge_date=snapshot["proxy_time"],
                )
            )
        except IndexError:  # no merge into target
            pass
        return alias_records

    def get_record_id(self, record: Alias) -> str:
        """
        Extract unique identifier from a MergeAliasRecord.

        Args:
            record: MergeAliasRecord object.

        Returns:
            str: Unique identifier combining ref_snp_id and merged_into.
        """
        return f"{record.ref_snp_id} -> {record.merged_into}"

    async def load(self, session, records: List[Alias]):
        """
        Insert RefSnpAlias records into the database.
        """
        aliases = []
        for alias_record in records:
            # Create RefSnpAlias ORM object with database-dependent fields
            aliases.append(
                RefSnpAlias(
                    **alias_record.model_dump(),
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
            )

        await RefSnpAlias.submit_many(session, aliases)
        return self.create_checkpoint(record=records[-1])
