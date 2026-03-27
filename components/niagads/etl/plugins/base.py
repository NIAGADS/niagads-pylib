import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union

import psutil
from niagads.common.core import ComponentBaseMixin
from niagads.common.types import ProcessStatus, ETLOperation
from niagads.database.session import DatabaseSessionManager
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.logger import ETLLogger
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.etl.plugins.types import (
    ETLLoadStrategy,
    ETLRunStatus,
    ResumeCheckpoint,
)
from niagads.etl.types import ETLExecutionMode
from niagads.database.genomicsdb.schema.admin.etl import ETLRun
from niagads.utils.asynchronous import null_async_context
from niagads.utils.list import chunker
from pydantic import ValidationError
from sqlalchemy import delete, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import IntegrityError


class AbstractBasePlugin(ABC, ComponentBaseMixin):
    """
    Abstract base class for ETL plugins (async).

    - Orchestrates ETL (extract -> transform -> load).

    """

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the ETL plugin base class.

        Args:
            params (BasePluginParams): Validated parameters for the plugin instance.
            name (Optional[str]): Optional name for the plugin instance (used for logging and identification).
        """
        super().__init__(debug=debug, verbose=verbose, initialize_logger=False)
        self.__metadata: PluginMetadata = self.__retrieve_plugin_metadata()

        self._name = name or self.__class__.__name__

        self.logger: ETLLogger = ETLLogger(
            name=self._name,
            log_file=self.__resolve_log_file_path(log_path),
            debug=self._debug,
        )

        try:
            if params["mode"] == ETLExecutionMode.UNDO:
                self._params = BasePluginParams(**params)
            else:
                self._params = self.parameter_model(**params)
        except ValidationError as err:
            BasePluginParams.log_validation_errors(err, self.logger)

        # parameter based properties
        self._mode = ETLExecutionMode(self._params.mode)
        self._batch_size: int = self._params.batch_size

        self.__start_time: Optional[datetime] = None
        self.__status_report: ETLRunStatus = None
        self.__checkpoint: ResumeCheckpoint = None
        self.__etl_run: ETLRun = None
        self.__transaction_record: Dict[str, Dict[str, int]] = {}
        self.__execution_status: ProcessStatus = None

        self._connection_string = (
            self._params.connection_string or PipelineSettings.from_env().DATABASE_URI
        )

        self.__session_manager = (
            self.__initialize_database_session() if not self.is_dry_run else None
        )

    def __retrieve_plugin_metadata(self) -> PluginMetadata:
        from niagads.etl.plugins.registry import PluginRegistry

        try:
            return PluginRegistry.get_metadata(self.__class__.__name__)
        except:
            raise KeyError(
                "Plugin not found in PluginRegistry; please use the registry decorator"
            )

    # -------------------------
    # Properties
    # -------------------------

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
        return self.__metadata.is_large_dataset

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
        return self.__metadata.version

    @property
    def is_dry_run(self) -> bool:
        """
        Indicates whether the plugin is running in DRY_RUN mode.
        """
        return self._mode == ETLExecutionMode.DRY_RUN

    @property
    def is_etl_run(self) -> bool:
        """
        Indicates whether plugin is doing a full RUN
        """
        return self._mode == ETLExecutionMode.RUN

    @property
    def commit(self) -> bool:
        """
        Indicates whether plugin is running in `COMMIT` mode
        """
        return self._params.commit

    @property
    def run_id(self):
        if self.is_etl_run:
            return self.__etl_run.run_id
        else:
            return None

    # -------------------------
    # Initialization helpers
    # -------------------------
    def __resolve_log_file_path(self, log_path: str):
        """
        Resolve the log file path for the plugin.

        If no path is specified, returns a standardized log file name in the
        current working directory.
        """
        if not log_path:
            return f"{self._name}.log"

        if ".log" in log_path:
            return log_path

        return os.path.join(log_path, f"{self._name}.log")

    def __initialize_database_session(self):
        if self._connection_string is None:
            raise ValueError(
                "Database connection string is required unless ETLMode is DRY_RUN."
            )

        return DatabaseSessionManager(
            connection_string=self._connection_string,
            echo=self._debug and self._verbose,
            expire_on_commit=False,
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
    async def load(self, session, transformed) -> Optional[ResumeCheckpoint]:
        """
        Persist transformed data using an async SQLAlchemy session.

        Args:
            session: Async SQLAlchemy session.
            transformed: The data to persist. For streaming, a list of records
            (buffer size <= batch_size). For bulk, the entire dataset.

        Returns:
            Optional[ResumeCheckpoint]: Checkpoint info (line/id) for resuming, or None.
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

    async def preprocess(self) -> None:
        """
        Hook for preprocessing stage

        Override in your plugin if preprocess actions are needed;
        runs preprocss and then exists.

        If you need the DB session, for preprocessing,
        use self.session_ctx() or self.session_manager() as best fits
        your application

        Extract expects result from preprocessing.
        """
        pass

    async def on_run_complete(self) -> None:
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

    async def undo(self) -> None:
        """
        Hook for undo method

        Override in your plugin if additional undo actions are needed;
        runs undo and then exists.

        If you need the DB session, for undo,
        use self.session_ctx() or self.session_manager() as best fits
        your application
        """

        async with self.session_ctx() as session:
            for table in self.affected_tables:
                try:
                    result = await session.execute(
                        delete(table).where(table.run_id == self._params.run_id)
                    )
                    self.inc_tx_count(table, ETLOperation.DELETE, result.rowcount)
                except IntegrityError:
                    raise IntegrityError(
                        f"Foreign key contraint violation."
                        f" Attempted to delete rows from {table.table_name()} before"
                        f" all child rows were removed. Order `affected_tables` in the "
                        f" plugin metadata so that they delete child records first."
                    )
            try:
                result = await session.execute(
                    delete(ETLRun).where(ETLRun.run_id == self._params.run_id)
                )
                self.inc_tx_count(ETLRun, ETLOperation.DELETE, result.rowcount)
            except IntegrityError:
                raise IntegrityError(
                    "Foreign key constraint violation. Child records for"
                    f" run_id = {self._params.run_id} still exist."
                    " Check `affected_tables` list."
                )
            if self.commit:
                await session.commit()
            else:
                await session.rollback()

    # -------------------------
    # Transaction Management
    # -------------------------

    def inc_tx_count(
        self,
        table: Union[str, Type[DeclarativeBase]],
        operation: ETLOperation = ETLOperation.INSERT,
        amount: int = 1,
    ):
        """
        Manually increment transaction count for explicit statement execution.

        Args:
            table: Table name (string) or SQLAlchemy table class.
            operation: ETLOperation type (INSERT, UPDATE, DELETE). Defaults to INSERT.
            amount: Number of records to increment by. Defaults to 1.
        """

        table_name = table if isinstance(table, str) else f"{table.table_name()}"
        if table_name not in self.__transaction_record:
            self.__transaction_record[table_name] = {}

        self.__transaction_record[table_name][str(ETLOperation(operation))] = (
            self.__transaction_record[table_name].get(str(ETLOperation(operation)), 0)
            + amount
        )

    def __get_total_transactions(self) -> int:
        """
        Calculate total transaction count from per-table self.__transaction_record.

        Returns:
            int: Total count of INSERT, UPDATE, DELETE across all tables.
        """
        total = 0
        for ops in self.__transaction_record.values():
            # Exclude SKIP operations from the total
            total += sum(
                count for op, count in ops.items() if op != str(ETLOperation.SKIP)
            )
        return total

    def __attach_etl_transaction_listener(self, session: AsyncSession) -> None:
        sync_session = session.sync_session
        if sync_session.info.get("etl_self.__transaction_record_listener_attached"):
            return

        sync_session.info["etl_self.__transaction_record_listener_attached"] = True

        event.listen(
            sync_session,
            "after_flush",
            self.__track_etl_transactions,
        )

    def __track_etl_transactions(self, sync_session, flush_context) -> None:
        """
        SQLAlchemy after_flush listener that tracks per-table inserts, updates, and deletes.

        Tracks across multiple flushes in the same session.

        Args:
            sync_session: The SQLAlchemy sync session (listeners not attached to async).
        """

        # Track new (INSERT) objects
        for obj in sync_session.new:
            table_name = (
                f"{obj.__class__.__table__.schema}.{obj.__class__.__table__.name}"
            )
            if table_name not in self.__transaction_record:
                self.__transaction_record[table_name] = {}
            self.__transaction_record[table_name][str(ETLOperation.INSERT)] = (
                self.__transaction_record[table_name].get(str(ETLOperation.INSERT), 0)
                + 1
            )

        # Track modified (UPDATE) objects
        for obj in sync_session.dirty:
            table_name = (
                f"{obj.__class__.__table__.schema}.{obj.__class__.__table__.name}"
            )
            if table_name not in self.__transaction_record:
                self.__transaction_record[table_name] = {}
            self.__transaction_record[table_name][str(ETLOperation.UPDATE)] = (
                self.__transaction_record[table_name].get(str(ETLOperation.UPDATE), 0)
                + 1
            )

        # Track deleted (DELETE) objects
        for obj in sync_session.deleted:
            table_name = (
                f"{obj.__class__.__table__.schema}.{obj.__class__.__table__.name}"
            )
            if table_name not in self.__transaction_record:
                self.__transaction_record[table_name] = {}
            self.__transaction_record[table_name][str(ETLOperation.DELETE)] = (
                self.__transaction_record[table_name].get(str(ETLOperation.DELETE), 0)
                + 1
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
            echo=self._debug,
        )

    async def __handle_transaction(
        self, session: AsyncSession, checkpoint: ResumeCheckpoint
    ) -> None:
        """
        Commit or rollback the session based on ETLMode and batch size logic.
        """
        tx_total = self.__get_total_transactions()
        msg = f"{tx_total} records"
        if self.commit:
            await session.commit()
            msg = f"COMMITTED {msg}"
        else:
            await session.rollback()
            msg = f"ROLLED BACK {msg}"

        # if transaction is successful, can update the checkpoint
        self.__checkpoint = checkpoint
        self.logger.info(
            f"{msg} - CHECKPOINT: {self.__checkpoint.as_info_string(self._debug)}"
        )

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

        if not buffer or (isinstance(buffer, list) and len(buffer) == 0):
            raise ValueError("Empty buffer (transformed) passed to load.")

        try:
            result: Optional[ResumeCheckpoint] = await self.load(session, buffer)
        except ValidationError as validation_error:
            if "ResumeCheckpoint" in str(validation_error):
                self.logger.warning(
                    f"Unable to generate resume checkpoint: {validation_error}"
                )
                result = ResumeCheckpoint(record_id="INVALID")
            raise validation_error
        except Exception:
            raise

        # result should be None or a ResumeCheckpoint
        if result and not isinstance(result, ResumeCheckpoint):
            raise TypeError(
                "Implementation Error: your plugin's load() must return None or a `ResumeCheckpoint`"
            )

        return result

    async def __flush_chunked_buffer(self, buffer, session) -> ResumeCheckpoint:
        checkpoint = None

        if not self.is_dry_run:
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
        is loaded, but commits and roll-backs happen according to `batch_size` parameter
        and according to ETL mode.
        """

        buffer: list = []
        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            if session is not None:
                self.__attach_etl_transaction_listener(session)
                for records in self.extract():
                    processed_records = self.transform(records)
                    # chunked can yield one or a list of records
                    if isinstance(processed_records, list):
                        buffer.extend(processed_records)
                    else:
                        buffer.append(processed_records)

                    if len(buffer) >= self._batch_size:
                        batches = chunker(
                            buffer, self._batch_size, return_iterator=True
                        )
                        for batch in batches:
                            if len(batch) == self._batch_size:
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
            if session is not None:
                self.__attach_etl_transaction_listener(session)
                # Bulk: load all at once, ignore batch_size
                checkpoint = None
                if not self.is_dry_run:
                    checkpoint = await self.__execute_load(session, processed_records)
                    await self.__handle_transaction(session, checkpoint)
                return checkpoint

    async def __process_bulk_in_batch_load(self):
        records = self.extract()
        processed_records = self.transform(records)
        batches = chunker(processed_records, self._batch_size, return_iterator=True)
        async with self.session_ctx(allow_null_if_unintialized=True) as session:
            if session is not None:
                self.__attach_etl_transaction_listener(session)
                for batch in batches:
                    checkpoint = await self.__flush_chunked_buffer(batch, session)
                    await self.__handle_transaction(session, checkpoint)

    async def __register_etl_run(self) -> Optional[int]:
        """
        Create plugin status trackers (internal status report) and ETLRun entry
        (if is_etl_run) in the database.
        No log entry if mode is other than `RUN`
        """
        if self.is_etl_run:
            try:
                self.__etl_run = ETLRun(
                    plugin_name=self._name,
                    plugin_version=self.version,
                    params=self._params.model_dump(
                        exclude_none=True, exclude_unset=True
                    ),
                    message="plugin run initiated",
                    status=self.__execution_status,
                    operation=str(self.operation),
                    start_time=self.__start_time,
                    rows_processed=0,
                    is_test_run=not self.commit,
                )

                # no if session is not None check here b/c I want to throw an error,
                # we should only reach this point if the session pool exists
                async with self.session_ctx() as session:
                    self.__etl_run.run_id = await self.__etl_run.submit(session)

                    # need to commit the etl run, regardless of commit mode
                    # to avoid roll back
                    await session.commit()
                    await self.__etl_run.detach(session)

            except Exception as err:
                self.logger.exception(
                    f"Failed to initialize ETL status trackers: {err}"
                )

        # do this second so can assign run_id correctly
        self.__status_report = ETLRunStatus(
            status=self.__execution_status,
            mode=self._mode,
            run_id=self.run_id,
            operation=(
                ETLOperation.DELETE
                if self._mode == ETLExecutionMode.UNDO
                else self.operation
            ),
            commit=self.commit,
        )

    async def __finalize_etl_run(
        self,
        message: str = None,
    ):
        """
        Update the plugin status trackers
        """

        total_transactions = self.__get_total_transactions()

        end_time = datetime.now()
        runtime = (end_time - self.__start_time).total_seconds()
        mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)

        self.__status_report.runtime = runtime
        self.__status_report.memory = mem_mb
        self.__status_report.status = self.__execution_status

        if self.is_dry_run:
            self.__status_report.estimated_transaction_count = total_transactions

        if self.is_etl_run:
            self.__etl_run.rows_processed = total_transactions
            self.__etl_run.end_time = end_time
            self.__etl_run.status = self.__execution_status
            self.__etl_run.message = message

            try:
                async with self.session_ctx() as session:
                    if session is not None:
                        await self.__etl_run.update(session)
                        await session.commit()
            except Exception as db_error:
                self.logger.exception(f"Failed to update ETLRun entry: {db_error}")

    def create_checkpoint(self, line=None, record=None) -> ResumeCheckpoint:
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
            record=record,
            record_id=self.get_record_id(record) if record is not None else None,
        )

    async def __summarize_transactions(self):
        """
        Summarize transaction counts for all affected tables.

        Uses accumulated per-table transaction self.__transaction_record from session events if available.
        Falls back to database queries for affected tables if self.__transaction_record is empty.

        Returns:
            dict: Mapping of table name to operation counts.
                If using auto-self.__transaction_record: {table_name: {INSERT: N, UPDATE: M, ...}}
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

    def __set_runtime_params(self, runtime_params):
        restore_params = None
        if runtime_params:
            restore_params = self._params.model_dump().copy()
            merged = self._params.model_dump().copy()
            merged.update(runtime_params)
            merged_params = self.parameter_model(**merged)
            self.logger.info(f"Runtime parameter overrides applied: {runtime_params}")
            self._params = merged_params
            self._batch_size = self._params.batch_size
        return restore_params

    async def __preprocess(self):
        # Preprocess mode - transformers write intermediary data to file
        if self._mode == ETLExecutionMode.PREPROCESS:
            await self.preprocess()
            self.__execution_status = ProcessStatus.SUCCESS

    async def __undo(self):
        if self._mode == ETLExecutionMode.UNDO:
            # checks here in case plugin overrides UNDO method
            if self.is_large_dataset:
                raise NotImplementedError(
                    "Batch UNDO for large datasets not yet implemented"
                )
            if self.affected_tables is None or len(self.affected_tables) == 0:
                self.logger.exception(
                    "No `affected tables` specified for this plugin.  Cannot UNDO."
                )
            if self._params.run_id is None:
                raise ValueError("Must specify ETL run_id to perform UNDO.")

            await self.undo()
            await self.__summarize_transactions()

            # If we reach here, ETL completed successfully
            self.__execution_status = ProcessStatus.SUCCESS

    async def __run(self):
        if self.is_etl_run or self.is_dry_run:
            async with self.session_ctx(allow_null_if_unintialized=True) as session:
                if session is not None:
                    await self.on_run_start(session)

            if self.load_strategy == ETLLoadStrategy.CHUNKED:
                await self.__process_chunked_load()
            elif self.load_strategy == ETLLoadStrategy.BULK:
                await self.__process_bulk_load()
            elif self.load_strategy == ETLLoadStrategy.BATCH:
                await self.__process_bulk_in_batch_load()
            else:
                raise RuntimeError(f"Unknown load strategy: {self.load_strategy}")

            await self.__summarize_transactions()
            await self.on_run_complete()

            # If we reach here, ETL completed successfully
            self.__execution_status = ProcessStatus.SUCCESS

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

        restore_params = self.__set_runtime_params(runtime_params)
        self.__execution_status = ProcessStatus.IN_PROGRESS
        self.__start_time = datetime.now()

        await self.__register_etl_run()

        self.logger.log_plugin_configuration(self._params)
        self.logger.log_plugin_run_start(self.run_id)

        error_message = None
        try:
            await self.__preprocess()
            await self.__undo()
            await self.__run()

        except Exception as err:
            # ETL failed
            self.__execution_status = ProcessStatus.FAIL
            error_message = f"ETL Plugin Run Failed: {err}"
            if self.is_etl_run:
                if self.__checkpoint is not None:
                    self.logger.checkpoint(self.__checkpoint)

            self.logger.exception(error_message)

        finally:
            await self.__finalize_etl_run(error_message)
            self.logger.status(self.__status_report)

            if runtime_params:  # restore plugin parameters
                self._params = self.parameter_model(**restore_params)

            return self.__execution_status
