"""
External Database Loader Plugin
- Loads a single ExternalDatabase record from a JSON configuration file.
"""

import json
from typing import Iterator

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.utils.string import matches
from pydantic import Field


class ExternalDatabaseLoaderParams(BasePluginParams):
    """Parameters for ExternalDatabaseLoader plugin."""

    file: str = Field(
        ..., description="full path to external database configuration file"
    )

    validate_file_exists = PathValidatorMixin.validator("file")


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

    def extract(self) -> Iterator[dict]:
        """
        Extract external database configuration from JSON file.

        Returns:
            Iterator[dict]: Single dictionary containing external database configuration.
        """
        with open(self._params.file, "r") as f:
            config = json.load(f)
        self.logger.debug(f"Extracted: {config}")
        return config

    async def transform(self, record: dict) -> ExternalDatabase:
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
        self.logger.debug(f"transformed = {xdbref}")
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

    async def __set_dataset_type(self, session, record: ExternalDatabase):
        if record.database_type_id is not None:
            try:
                term_pk = await OntologyTerm.find_primary_key(
                    session, curie=record.database_type_id
                )
            except:
                raise ValueError(
                    f"Invalid dataset_type: {record.database_type_id} - CURIE not found in DB"
                )
        record.database_type_id = term_pk

    async def load(self, session, record: ExternalDatabase):
        """
        Insert a single ExternalDatabase record into the database.

        Args:
            session: Async SQLAlchemy session.
            transformed: ExternalDatabase record to insert.

        Returns:
            ETLLoadResult: checkpoint and transaction count
        """

        if not await ExternalDatabase.record_exists(
            session, {"name": record.name, "version": record.version}
        ):
            await self.__set_dataset_type(session, record)
            await record.submit(session)
        else:
            self.logger.warning(
                f"External Database Reference {record.database_key}: {record.name}|{record.version} already exists"
            )
            self.inc_tx_count(ExternalDatabase, ETLOperation.SKIP)

        return self.create_checkpoint(record=record)
