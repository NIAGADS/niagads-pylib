"""
External Database Loader Plugin
- Loads a single ExternalDatabase record from a JSON configuration file.
"""

import json
from typing import Any, Dict, Iterator, List, Optional, Type

from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    JSONConfigValidatorMixin,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadResult, ETLLoadStrategy
from niagads.etl.plugins.types import ETLOperation
from niagads.genomicsdb.schema.reference.externaldb import ExternalDatabase
from pydantic import Field

# FIXME: I'm being silly w/this let's leverage pydantic/sqlalachemy


class ExternalDatabaseLoaderParams(BasePluginParams, JSONConfigValidatorMixin):
    """Parameters for ExternalDatabaseLoader plugin."""

    file: str = Field(..., description="full path to JSON configuration file")

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)
    validate_config = JSONConfigValidatorMixin.validator("file", ExternalDatabase)


metadata = PluginMetadata(
    version="1.0",
    description=(
        f"ETL Plugin to load an ExternalDatabase record from a JSON"
        f" configuration file into {ExternalDatabase.table_name()}."
    ),
    affected_tables=[ExternalDatabase],
    load_strategy=ETLLoadStrategy.BULK,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=ExternalDatabaseLoaderParams,
)


@PluginRegistry.register(metadata)
class ExternalDatabaseLoader(AbstractBasePlugin):
    """
    ETL plugin for loading a single ExternalDatabase record from a JSON configuration file.
    """

    _params: ExternalDatabaseLoaderParams  # type annotation

    def __init__(self, params: Dict[str, Any], name: Optional[str] = None):
        super().__init__(params, name)

    def extract(self) -> Iterator[dict]:
        """
        Extract external database configuration from JSON file.

        Returns:
            Iterator[dict]: Single dictionary containing external database configuration.
        """
        with open(self._params.file, "r") as f:
            config = json.load(f)
        return config

    def transform(self, record: dict) -> ExternalDatabase:
        """
        Convert a record (JSON config) dict to an ExternalDatabase object.

        Args:
            record: Dictionary with ExternalDatabase configuration .

        Returns:
            ExternalDatabase: Transformed database record.
        """
        if record is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )

        xdbref = ExternalDatabase(**record)
        xdbref.run_id = self.run_id
        return xdbref

    def get_record_id(self, record: ExternalDatabase) -> str:
        """
        Returns a unique identifier for a record (database_key).

        Args:
            record: The ExternalDatabase record.

        Returns:
            str: The unique identifier.
        """
        return record.database_key

    async def load(self, session, transformed: ExternalDatabase) -> ETLLoadResult:
        """
        Insert a single ExternalDatabase record into the database.

        Args:
            session: Async SQLAlchemy session.
            transformed: ExternalDatabase record to insert.

        Returns:
            ETLLoadResult: checkpoint and transaction count
        """
        if not ExternalDatabase.record_exists(
            session, {"name": transformed.name, "version": transformed.version}
        ):
            await transformed.submit(session)
        else:
            self.logger.warning(
                f"External Database Reference {transformed.database_key}: {transformed.name}|{transformed.version} already exists"
            )
        return ETLLoadResult(
            checkpoint=ResumeCheckpoint(record=self.get_record_id(transformed)),
            transaction_count=1,
        )
