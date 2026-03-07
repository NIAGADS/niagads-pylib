import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Type

from niagads.etl.plugins.metadata import PluginMetadata
import psutil
from niagads.common.core import ComponentBaseMixin
from niagads.common.types import ProcessStatus
from niagads.database.session import DatabaseSessionManager
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.logger import ETLLogger
from niagads.etl.plugins.parameters import BasePluginParams

from niagads.etl.plugins.types import (
    ETLLoadResult,
    ETLLoadStrategy,
    ETLOperation,
    ETLRunStatus,
    ResumeCheckpoint,
)
from niagads.etl.types import ETLMode
from niagads.genomicsdb.schema.admin.etl import ETLRun
from niagads.utils.asynchronous import null_async_context
from niagads.utils.list import chunker
from niagads.utils.logging import FunctionContextLoggerWrapper
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class AbstractBasePlugin(ABC, ComponentBaseMixin):
    """
    Abstract base class for ETL plugins (async).

    - Orchestrates ETL (extract -> transform -> load).
    - JSON logging only, with checkpoint logs discoverable by "message":"CHECKPOINT".
    - Dry-run by default; --commit flips to actual DB writes.
    - Resume:
        * extract() should honor resume_from.line (skip lines before that).
        * transform() may honor resume_from.id (skip until matching ID).
    - Chunked loading is a class property (`chunked`).
        * chunked: records processed in chunks of size determined by the plugin (chunk_size >= 1).
        * bulk: extract->transform over entire dataset; load() called once with bulk data.

    Note:
        The `run` method supports runtime parameter overrides, which are applied only for the
        duration of the run and do not mutate the instance's original parameters.

    Plugins must implement `load()` using self.session_manager.session() (async).
    Plugins decide when to commit inside load() (per buffer/batch) — pipeline does NOT auto-commit.
    """

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
    ):
        """
        Initialize the ETL plugin base class.

        Args:
            params (BasePluginParams): Validated parameters for the plugin instance.
            name (Optional[str]): Optional name for the plugin instance (used for logging and identification).
        """
        # parameter model enforcement
        # allow subclasses to add fields via their own model; we validate here
        model: Type[BasePluginParams] = self.parameter_model()
        self._params = model(**params)

        super().__init__(debug=self._params.debug, verbose=self._params.verbose)

        self.__metadata: PluginMetadata = self.__retrieve_plugin_metadata()

        self._name = name or self.__class__.__name__
        self.__start_time: Optional[datetime] = None
        self.__status_report: ETLRunStatus = None
        self.__checkpoint: ResumeCheckpoint = None
        self.__etl_run: ETLRun = None
        self.__total_transactions: int = None
        self.__transaction_record: Dict[str, Dict[str, int]] = {}

        # parameter based properties
        self._mode = ETLMode(self._params.mode)
        self._commit_after: int = self._params.commit_after

        self.logger: ETLLogger = FunctionContextLoggerWrapper(
            ETLLogger(
                name=self._name,
                log_file=self.__resolve_log_file_path(),
                debug=self._debug,
            )
        )

        self._connection_string = (
            self._params.connection_string or PipelineSettings.from_env().DATABASE_URI
        )

        self.__session_manager = (
            self.__initialize_database_session() if not self.is_dry_run else None
        )

    # -------------------------
    # Properties
    # -------------------------

    def __retrieve_plugin_metadata(self) -> PluginMetadata:
        from niagads.etl.plugins.registry import PluginRegistry

        try:
            return PluginRegistry._metadata.get(self.__class__.__name__)
        except:
            raise KeyError(
                "Plugin not found in PluginRegistry; please use the registry decorator"
            )

    @property
    def parameter_model(self) -> Type[BasePluginParams]:
        """
        Return the Pydantic parameter model for this plugin.

        Returns:
            Type[BasePluginParams]: The Pydantic model class (must subclass BasePluginParams).
        """
        return self.__metadata.parameter_model

    @property
    def operation(self) -> ETLOperation:
        """
        Get the ETLOperation type used for rows created by this plugin run.

        Returns:
            ETLOperation: The operation type for this plugin's output rows.
        """
        return self.__metadata.operation

    @property
    def affected_tables(self) -> list[Type[DeclarativeBase]]:
        """
        Get the list of database tables this plugin writes to.

        Returns:
            List[Type[DeclarativeBase]]: List of table classes
        """
        return self.__metadata.affected_tables

    @property
    def is_large_dataset(self) -> bool:
        self.__metadata.is_large_dataset

    @property
    def load_strategy(self) -> ETLLoadStrategy:
        """
        Whether the plugin processes records in chunks, in bulk, or in batch.

        Returns:
            ETLLoadStrategy
        """
        return self.__metadata.load_strategy

    @property
    def description(self) -> str:
        """
        Detail description and usage caveats forthe plugin.

        Returns:
            str: The description
        """
        return self.__metadata.description

    @property
    def version(self):
        self.__metadata.version

    @property
    def is_dry_run(self) -> bool:
        """
        Indicates whether the plugin is running in DRY_RUN mode.
        """
        return self._mode == ETLMode.DRY_RUN

    @property
    def run_id(self):
        if not self.is_dry_run:
            return self.__etl_run.etl_run_id
        else:
            return None

    @property
    def tx_count(self):
        return self.__total_transactions

    @tx_count.setter
    def tx_count(self, value):
        self.__total_transactions = value

    def inc_tx_count(self, amount=1):
        """
        Increment the transaction (tx) counter

        Args:
            amount (int, optional): increment amount. Defaults to 1.
        """
        if self.__total_transactions is None:
            self.__total_transactions = 0
        self.__total_transactions += amount

    # -------------------------
    # Initialization helpers
    # -------------------------
    def __resolve_log_file_path(self):
        """
        Resolve the log file path for the plugin.

        If no path is specified, returns a standardized log file name in the
        current working directory.
        """
        if not self._params.log_path:
            return f"{self._name}.log"

        if ".log" in self._params.log_path:
            return self._params.log_path

        return os.path.join(self._params.log_path, f"{self._name}.log")

    def __initialize_database_session(self):
        if self._connection_string is None:
            raise ValueError(
                "Database connection string is required unless ETLMode is DRY_RUN."
            )

        return DatabaseSessionManager(
            connection_string=self._connection_string,
            echo=self._debug,
            enable_etl_tracking=True,
        )

    # -------------------------
    # Abstract contract
    # -------------------------

    @abstractmethod
    def extract(self):
        """
        Extract parsed records from the data source.

        Resume Behavior:
            If self.params.get('resume_from', {}).get('line') is set, fast-forward
            the source to that line before yielding (plugins implement the logic).

        Returns:
            Iterator or iterable:
                - If streaming=True: An iterator/generator yielding records.
                - If streaming=False: A dataset (list/iterable/dataframe) for bulk processing.
        """
        ...

    @abstractmethod
    def transform(self, data):
        """
        Transform extracted data.

        Resume Behavior:
            If self.params.get('checkpoint', {}).get('id') is set, you may return
            None for records until the matching ID is encountered; then return a
            transformed record thereafter.

        Args:
            data: The extracted data to transform.

        Returns:
            - If streaming=True: Transformed single record or None (to skip).
            - If streaming=False: Transformed dataset (iterable/collection).
        """
        ...

    @abstractmethod
    async def load(self, session, transformed) -> ETLLoadResult:
        """
        Persist transformed data using an async SQLAlchemy session.

        Args:
            session: Async SQLAlchemy session.
            transformed: The data to persist. For streaming, a list of records
            (buffer size <= commit_after). For bulk, the entire dataset.

        Returns:
            ResumeCheckpoint: Contains count of rows persisted and checkpoint info (line/id).
        """
        ...

    @abstractmethod
    def get_record_id(self, record: Any) -> str:
        """
        Return the unique identifier for a record, used for checkpointing.

        Args:
            record: The record to extract the ID from.
        Returns:
            str: The unique identifier for the record.
        """
        ...

    # -------------------------
    # Overridable Lifecycle Hooks
    # -------------------------

    def on_run_complete(self) -> None:
        """
        Hook for plugins to perform custom operations after the end of a run.
        This may include additional logging or intermediary file cleanup.

        Override in your plugin if custom post-run actions are needed;
        otherwise, leave as pass.
        """
        pass

    async def on_run_start(self, session) -> None:
        """
        Hook for plugins to perform custom operations at the start of a run.
        This may include initialization, validation, or setup operations.

        Passes session to plugin instance to allow DB-based validations
        (e.g., xdbref) if not DRY_RUN.  It is the responsiblity of the
        plugin developer to check run mode before attempting to validate against
        the database.

        Override in your plugin if custom pre-run actions are needed;
        otherwise, leave as pass.
        """
        pass

    @property
    def has_preprocess_mode(self) -> bool:
        """
        Indicates whether the plugin supports preprocessing mode.
        Subclasses may override to enable/disable preprocessing.
        """
        return False

    # -------------------------
    # Transaction Management
    # -------------------------

    def __update_transaction_record(self, session: AsyncSession) -> None:
        """
        Extract per-table transaction tracking from session and merge into
        plugin's cumulative transaction tracking dict.

        Accumulates across multiple sessions/flushes. Skips if session does not
        have _etl_tracking attribute.

        Args:
            session (AsyncSession): The database session with potential _etl_tracking.
        """
        if not hasattr(session, "_etl_tracking"):
            raise RuntimeError(
                "For some unexplained reason etl_tracking was not initialized in the session and yet we still reached this point."
            )

        transaction_record = session._etl_tracking
        for table_name, operations in transaction_record.items():
            if table_name not in self.__transaction_record:
                self.__transaction_record[table_name] = {}
            for op, count in operations.items():
                self.__transaction_record[table_name][op] = (
                    self.__transaction_record[table_name].get(op, 0) + count
                )

    def session_ctx(self, allow_null_if_unintialized: bool = False):
        """
        Async context manager for obtaining a database session, intended for use
        with 'async with'.

        Args:
            allow_null_if_unintialized (bool): If True, returns a nullcontext()
                if the session manager is not initialized (i.e., in dry-run mode),
                instead of raising an error. If False, raises ValueError when the
                session manager is not available.

        Returns:
            Async context manager: Use with 'async with' to yield a database
                session, or a null context if the session manager is not initialized
                and allow_null_if_unintialized is True.

        Example:
            async with self.session_ctx(allow_null_if_unintialized=True) as session:
                # use session here
                ...
        """
        if self.__session_manager is None:
            if allow_null_if_unintialized:
                return null_async_context()
            else:
                raise ValueError(
                    "Database session is not initialized, cannot return session context."
                )

        return self.__session_manager.session_ctx()

    def session_manager(self, pool_size: int = 1):
        """
        Create a new DatabaseSessionManager instance with the given pool size.

        This is used for preprocessing steps that require database lookups or
        for parallel ETL loads that need separate session managers.

        Args:
            pool_size (int): The number of connections in the session pool. Default is 1.

        Returns:
            DatabaseSessionManager: A new session manager instance configured with the
                current connection string and debug settings.
        """
        return DatabaseSessionManager(
            self._connection_string,
            pool_size=pool_size,
            enable_etl_tracking=True,
            echo=self._debug,
        )

    async def __handle_transaction(
        self, session: AsyncSession, checkpoint: ResumeCheckpoint
    ) -> None:
        """
        Commit or rollback the session based on ETLMode and commit_after logic.
        """
        msg = f"{self.__total_transactions} records"
        if self._mode == ETLMode.COMMIT:
            await session.commit()
            self.logger.info("COMMITED", msg)
        elif self._mode == ETLMode.NON_COMMIT:
            await session.rollback()
            self.logger.info("ROLLED BACK", msg)

        # if transaction is successful, can update the checkpoint
        self.__checkpoint = checkpoint

    async def __execute_load(self, session, buffer) -> ResumeCheckpoint:
        """
        Loads data and performs validations.

        Args:
            buffer: The records to load.
            session: Async SQLAlchemy session.

        Returns:
            ResumeCheckpoint or None: Checkpoint object returned by load(), or None if not implemented.

        Raises:
            TypeError: If load() does not return a valid response.
            RuntimeError: If no transaction counts were updated during a non-empty transaction.
        """

        if not buffer or len(buffer) == 0:
            raise ValueError("Empty buffer (transformed) passed to load.")

        result: ETLLoadResult = await self.load(session, buffer)

        if not isinstance(result, ETLLoadResult):
            raise TypeError(
                "Implementation Error: `your plugin's load()` must return an `ETLLoadResult`, including a "
                "checkpoint (nullable) and transaction_count >= 0"
            )

        # Merge per-table transaction tracking from session (if available)
        self.__update_transaction_record(session)

        # increment transaction count (for backward compatibility with plugins
        # that manually track)
        self.inc_tx_count(result.transaction_count)

        checkpoint = result.checkpoint

        # a plugin may not have checkpoint handling so
        # returning None is okay
        if checkpoint and not isinstance(checkpoint, ResumeCheckpoint):
            raise TypeError(
                "Implementation Error: your plugin's load() must return None or a `ResumeCheckpoint`; "
                "for the checkpoint value"
            )

        return checkpoint

    async def __flush_chunked_buffer(self, buffer, session) -> ResumeCheckpoint:
        checkpoint = None

        if self.is_dry_run:
            try:
                estimated_tx_count = len(buffer)
            except TypeError:  # handle iterators/generators
                estimated_tx_count = sum(1 for _ in buffer)
            self.inc_tx_count(estimated_tx_count)
        else:
            checkpoint = await self.__execute_load(session, buffer)

        # Clear buffer if it's a list, else set to None to release reference
        if isinstance(buffer, list):
            buffer.clear()
        else:
            buffer = None
        return checkpoint

    async def __process_chunked_load(self):
        """
        Process records in chunks and load them into the database.

        Chunks are processed with size determined by extract. Each chunk
        is loaded, but commits and roll-backs happen according to `commit_after` parameter
        and according to ETL mode.
        """

        buffer: list = []
        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            for records in self.extract():
                processed_records = self.transform(records)
                # chunked can yield one or a list of records
                if isinstance(processed_records, list):
                    buffer.extend(processed_records)
                else:
                    buffer.append(processed_records)

                if len(buffer) >= self._commit_after:
                    batches = chunker(buffer, self._commit_after, returnIterator=True)
                    for batch in batches:
                        if len(batch) == self._commit_after:
                            checkpoint = await self.__flush_chunked_buffer(
                                batch, session
                            )
                            await self.__handle_transaction(session, checkpoint)
                        else:
                            buffer = batch  # residuals

            # residuals
            if buffer:
                checkpoint = await self.__flush_chunked_buffer(buffer, session)
                await self.__handle_transaction(session, checkpoint)

    async def __process_bulk_load(self) -> ResumeCheckpoint:
        records = self.extract()
        processed_records = self.transform(records)

        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            # Bulk: load all at once, ignore commit_after
            if self.is_dry_run:
                try:
                    estimated_tx_count = len(processed_records)
                except TypeError:  # handle iterators/generators
                    estimated_tx_count = sum(1 for _ in processed_records)
                self.inc_tx_count(estimated_tx_count)
                return None
            else:
                checkpoint = await self.__execute_load(session, processed_records)
                await self.__handle_transaction(session, checkpoint)
                return checkpoint

    async def __process_bulk_in_batch_load(self):
        records = self.extract()
        processed_records = self.transform(records)
        batches = chunker(processed_records, self._commit_after, returnIterator=True)
        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            for batch in batches:
                checkpoint = await self.__flush_chunked_buffer(batch, session)
                await self.__handle_transaction(session, checkpoint)

    async def __initialize_etl_run(self) -> Optional[int]:
        """
        Log the start of a plugin run in the database.
        No log entry is created if ETLMode is DRY_RUN.
        """
        self.__etl_run = ETLRun(
            plugin_name=self._name,
            plugin_version=self.version,
            params=self._params.model_dump(),
            message="plugin run initiated",
            status=ProcessStatus.RUNNING,
            operation=str(self.operation),
            start_time=self.__start_time,
            rows_processed=0,
        )

        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            run_id = self.__etl_run.submit(session)

        self.__etl_run.run_id = run_id

    async def __finalize_etl_run(
        self,
        end_time,
        status: ProcessStatus,
        rows_processed: int = None,
        message: str = None,
    ):
        """
        Update the plugin task in the database at plugin completion.
        Sets rows_processed, end_time, status, and message.
        """

        self.__etl_run.rows_processed = rows_processed
        self.__etl_run.end_time = end_time
        self.__etl_run.status = status
        self.__etl_run.message = message

        async with self.session_ctx() as session:
            await self.__etl_run.update(session)

    def set_checkpoint(self, line=None, record=None) -> ResumeCheckpoint:
        """
        Generate a checkpoint for the current ETL state.

        Args:
            line (int): The line number or position in the input data.
            record (Any): The current record to checkpoint.

        Returns:
            ResumeCheckpoint: Checkpoint object for resuming ETL from this state.
        """
        if line is None and record is None:
            raise ValueError("Must set either line or record to non-None")
        return ResumeCheckpoint(
            line=line,
            full_record=record,
            record=self.get_record_id(record) if record is not None else None,
        )

    async def __summarize_transactions(self):
        """
        Summarize transaction counts for all affected tables.

        Uses accumulated per-table transaction tracking from session events if available.
        Falls back to database queries for affected tables if tracking is empty.

        Returns:
            dict: Mapping of table name to operation counts.
                If using auto-tracking: {table_name: {INSERT: N, UPDATE: M, ...}}
                If using database queries: {schema.table: count}
        """
        # Fallback: query affected tables (legacy behavior)
        if self.affected_tables is None or self.is_dry_run:
            self.__status_report.transaction_record = {}

        # Use auto-tracked transactions if available
        if self.__transaction_record:
            self.__status_report.transaction_record = self.__transaction_record
            return

    # -------------------------
    # Run orchestration
    # -------------------------

    async def run(
        self,
        runtime_params: Optional[Dict[str, Any]] = None,
    ) -> ProcessStatus:
        """
        Execute the ETL process for this plugin instance.

        Args:
            runtime_params (Optional[Dict[str, Any]]):
                Runtime parameter overrides, merged atop validated self.params for this run only.
                The instance's original parameters are restored after the run.

        Returns:
            ProcessStatus: SUCCESS if ETL completed, FAIL otherwise.
        """
        merged_params = None
        execution_status = None
        restore_params = None
        if runtime_params:
            restore_params = self._params.model_dump().copy()
            merged = self._params.model_dump().copy()
            merged.update(runtime_params)
            merged_params = self.parameter_model(**merged)
            self.logger.info(f"Runtime parameter overrides applied: {runtime_params}")
            self._params = merged_params
            self._commit_after = self._params.commit_after

        self.__start_time = datetime.now()

        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            await self.on_run_start(session)

        # Preprocess mode - transformers write intermediary data to file
        if self._mode == ETLMode.PREPROCESS:
            try:
                if not self.has_preprocess_mode:
                    raise RuntimeError(
                        "No preprocess method implemented; cannot run in `PREPROCESS` mode."
                    )
                self.logger.log_plugin_configuration(self._params)
                raw_data = self.extract()
                self.transform(raw_data)
                execution_status = ProcessStatus.SUCCESS
            except Exception as e:
                execution_status = ProcessStatus.FAIL
                self.logger.exception(f"Preprocess failed: {e}")

            return execution_status

        # Regular ETL modes
        try:
            await self.__initialize_etl_run()
            execution_status = ProcessStatus.RUNNING
            self.__status_report = ETLRunStatus(
                status=execution_status,
                mode=self._mode,
                run_id=self.run_id,
                operation=self.operation,
            )

        except Exception as e:
            self.logger.exception(f"Failed to initialize plugin: {e}")
            raise RuntimeError(f"Failed to initialize plugin: {e}")

        try:
            self.logger.log_plugin_configuration(self._params)
            self.logger.log_plugin_run()

            if self.load_strategy == ETLLoadStrategy.CHUNKED:
                await self.__process_chunked_load()
            elif self.load_strategy == ETLLoadStrategy.BULK:
                await self.__process_bulk_load()
            elif self.load_strategy == ETLLoadStrategy.BATCH:
                await self.__process_bulk_in_batch_load()
            else:
                raise RuntimeError(f"Unknown load strategy: {self.load_strategy}")

            # If we reach here, ETL completed successfully
            execution_status = ProcessStatus.SUCCESS

        except Exception as e:
            # ETL failed
            execution_status = ProcessStatus.FAIL

            # checkpoint for resume (line + record snapshot)
            checkpoint_kwargs = {
                "error": e,
            }

            if self.__checkpoint is not None:
                if self.__checkpoint.line is not None:
                    checkpoint_kwargs["line"] = self.__checkpoint.line
                if self.__checkpoint.full_record is not None:
                    record_obj = self.__checkpoint.full_record
                    # Use model_dump if record is a Pydantic model
                    if hasattr(record_obj, "model_dump") and callable(
                        record_obj.model_dump
                    ):
                        checkpoint_kwargs["record"] = record_obj.model_dump()
                    else:
                        checkpoint_kwargs["record"] = record_obj
                if self.__checkpoint.record is not None:
                    checkpoint_kwargs["record_id"] = self.__checkpoint.record
                elif self.__checkpoint.full_record is not None:
                    checkpoint_kwargs["record_id"] = self.get_record_id(
                        self.__checkpoint.full_record
                    )

            self.logger.checkpoint(**checkpoint_kwargs)
            self.logger.exception(f"Plugin failed: {e}")

            # --- Finalize plugin run log on error (except DRY_RUN) ---
            if self.run_id:
                await self.__finalize_etl_run(
                    datetime.now(),  # end time
                    execution_status,
                    message=f"ETL run failed: {e}",
                    rows_processed=self.__total_transactions,
                )
        finally:
            self.on_run_complete()

            # log status
            end_time = datetime.now()
            runtime = (end_time - self.__start_time).total_seconds()
            mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self.__status_report.runtime = runtime
            self.__status_report.memory = mem_mb
            self.__status_report.status = execution_status
            if self.is_dry_run:
                self.__status_report.estimated_transaction_count = (
                    self.__total_transactions
                )
            await self.__summarize_transactions()
            self.logger.status(self.__status_report)

            try:
                if self.run_id:
                    await self.__finalize_etl_run(
                        end_time,
                        execution_status,
                        rows_processed=self.__total_transactions,
                    )

            except Exception as db_error:
                self.logger.exception(f"Failed to update plugin task in DB: {db_error}")

            if runtime_params:  # restore plugin parameters
                self._params = self.parameter_model(**restore_params)

        return execution_status
