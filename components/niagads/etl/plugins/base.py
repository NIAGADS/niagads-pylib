from contextlib import nullcontext
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import auto
from typing import Any, Dict, List, Optional, Type

from niagads.utils.list import chunker
import psutil
from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.config import ETLMode
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.logger import ETLLogger, ETLStatusReport
from niagads.etl.plugins.parameters import BasePluginParams, ResumeCheckpoint
from niagads.genomicsdb.schema.admin.pipeline import ETLOperation, ETLRun
from niagads.utils.logging import FunctionContextLoggerWrapper


class LoadStrategy(CaseInsensitiveEnum):
    CHUNKED = auto()
    BULK = auto()
    BATCH = auto()


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
        The `run` method supports runtime parameter overrides, which are applied only for the duration of the run and do not mutate the instance's original parameters.

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

        self._name = name or self.__class__.__name__
        self.__start_time: Optional[datetime] = None
        self._mode = self._params.mode
        self.__status_report: ETLStatusReport = None
        self.__checkpoint: ResumeCheckpoint = None

        # members initialized from validated params
        self._commit_after: int = self._params.commit_after
        self._run_id = self._params.run_id or uuid.uuid4().hex[:8].upper()

        self.logger: ETLLogger = FunctionContextLoggerWrapper(
            ETLLogger(
                name=self._name,
                log_file=self.__resolve_log_file_path(),
                run_id=self._run_id,
                plugin=self._name,
                debug=self._debug,
            )
        )

        if self._debug:
            self.logger.level = "DEBUG"

        self._connection_string = (
            self._params.connection_string or PipelineSettings.from_env().DATABASE_URI
        )

        if self._connection_string is None and self._mode is not ETLMode.DRY_RUN:
            self.logger.warning(
                f"No DB connection string provided. Setting ETLMode to `DRY_RUN`"
            )
            self._mode = ETLMode.DRY_RUN

        if self._mode != ETLMode.DRY_RUN:
            # don't attempt to connect to DB on dry runs
            self.__session_manager = DatabaseSessionManager(
                connection_string=self._connection_string, echo=self._debug
            )
        else:
            self.__session_manager = None

    @property
    def is_dry_run(self) -> bool:
        """
        Indicates whether the plugin is running in DRY_RUN mode.
        """
        return self._mode == ETLMode.DRY_RUN

    @property
    def has_preprocess_mode(self) -> bool:
        """
        Indicates whether the plugin supports preprocessing mode.
        Subclasses may override to enable/disable preprocessing.
        """
        return False

    @property
    def status_report(self):
        return self.__status_report

    @property
    def version(self):
        # Local import to avoid circular import
        from niagads.etl.plugins.registry import PluginRegistry

        return PluginRegistry.describe(self.__class__.__name__).get("version")

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

    # -------------------------
    # Abstract contract
    # -------------------------
    @classmethod
    @abstractmethod
    def description(cls) -> str:
        """
        Detail description and usage caveats forthe plugin.

        Returns:
            str: The description
        """
        ...

    @classmethod
    @abstractmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        """
        Return the Pydantic parameter model for this plugin.

        Returns:
            Type[BasePluginParams]: The Pydantic model class (must subclass BasePluginParams).
        """
        ...

    @property
    @abstractmethod
    def operation(self) -> ETLOperation:
        """
        Get the ETLOperation type used for rows created by this plugin run.

        Returns:
            ETLOperation: The operation type for this plugin's output rows.
        """
        ...

    @property
    @abstractmethod
    def affected_tables(self) -> List[str]:
        """
        Get the list of database tables this plugin writes to.

        Returns:
            List[str]: List of affected table names.
        """
        ...

    @property
    @abstractmethod
    def load_strategy(self) -> LoadStrategy:
        """
        Whether the plugin processes records in chunks, in bulk, or in batch.

        Returns:
            LoadStrategy
        """
        ...

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
    async def load(self, transformed, session) -> ResumeCheckpoint:
        """
        Persist transformed data using an async SQLAlchemy session.

        IMPLEMENTER WARNING:
        You MUST tally all updates and inserts using self.update_transaction_count
        for every record processed in your load() implementation. This is required
        for accurate ETL status reporting.

        Args:
            transformed: The data to persist. For streaming, a list of records (buffer size <= commit_after). For bulk, the entire dataset.
            session: Async SQLAlchemy session.

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

    def on_run_complete(self) -> None:
        """
        Hook for plugins to perform custom operations after the end of a run.
        This may include additional logging or intermediary file cleanup.

        Override in your plugin if custom post-run actions are needed;
        otherwise, leave as pass.
        """
        pass

    # -------------------------
    # Transaction Management
    # -------------------------

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
                session, or nullcontext() if the session manager is not initialized
                and allow_null_if_unintialized is True.

        Example:
            async with self.session_ctx(allow_null_if_unintialized=True) as session:
                # use session here
                ...
        """
        if self.__session_manager is None:
            if allow_null_if_unintialized:
                return nullcontext()
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
            self._connection_string, pool_size=pool_size, echo=self._debug
        )

    async def __handle_transaction(self, session, checkpoint: ResumeCheckpoint) -> None:
        """
        Commit or rollback the session based on ETLMode and commit_after logic.
        """
        total_transactions = self.__status_report.total_writes()
        msg = f"{total_transactions} records"
        if self._mode == ETLMode.COMMIT:
            await session.commit()
            self.logger.info("COMMITED", msg)
        elif self._mode == ETLMode.NON_COMMIT:
            await session.rollback()
            self.logger.info("ROLLED BACK", msg)

        # if transaction is successful, can update the checkpoint
        self.__checkpoint = checkpoint

    def __handle_dry_run(self, count: int):
        """
        Helper for DRY_RUN mode: update transaction count for the correct table.
        Args:
            count (int): Number of records to count as processed.
        """
        table = self.affected_tables[0] if len(self.affected_tables) == 1 else "DRY.RUN"
        self.update_transaction_count(self.operation, table, count)

    async def __execute_load(self, buffer, session) -> ResumeCheckpoint:
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

        checkpoint = await self.load(buffer, session)

        # a plugin may not have checkpoint handling so
        # returning None is okay
        if checkpoint and not isinstance(checkpoint, ResumeCheckpoint):
            raise TypeError(
                "Implementation Error: your plugin's load() must return None or a `ResumeCheckpoint`; "
                "see `components.niagads.etl.plugins.base.ResumeCheckpoint`."
            )

        # basically not checking previous count b/c only care if this
        # fails the first time; if the implemeter forgot to count transactions
        # it should fail with first "batch"
        transaction_count = (
            self.__status_report.total_writes() + self.__status_report.total_skips()
        )

        if transaction_count == 0:
            raise RuntimeError(
                "Implementation Error: No transaction counts were updated in load(); "
                "please call self.update_transaction_count to update counts of INSERTS/UPDATES/SKIPS."
            )

        return checkpoint

    async def __flush_chunked_buffer(self, buffer, session) -> ResumeCheckpoint:
        checkpoint = None

        if self.is_dry_run:
            try:
                count = len(buffer)
            except TypeError:  # handle iterators/generators
                count = sum(1 for _ in buffer)
            self.__handle_dry_run(count)
        else:
            checkpoint = await self.__execute_load(buffer, session)

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
            if self._mode == ETLMode.DRY_RUN:
                try:
                    count = len(processed_records)
                except TypeError:  # handle iterators/generators
                    count = sum(1 for _ in processed_records)
                self.__handle_dry_run(count)
                return None
            else:
                checkpoint = await self.__execute_load(processed_records, session)
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

    async def __db_log_plugin_run(self) -> Optional[int]:
        """
        Log the start of a plugin run (except DRY_RUN). Returns the log row's ID, or None if not logged.
        """
        if self._mode == ETLMode.DRY_RUN:
            return ETLMode.DRY_RUN

        async with self._session_manager() as session:
            task = ETLRun(
                plugin_name=self._name,
                plugin_version=self.version,
                params=self._params.model_dump(),
                message="plugin run initiated",
                status=ProcessStatus.RUNNING,
                operation=self.operation.value,
                run_id=self._run_id,
                start_time=self.__start_time,
                rows_processed=0,
            )
            session.add(task)
            await session.commit()
        return task.run_id

    async def __db_update_plugin_task(
        self,
        run_id: int,
        end_time,
        status: ProcessStatus,
        rows_processed: int = None,
        message: str = None,
    ):
        """
        Update the plugin task in the database at plugin completion.
        Sets rows_processed, end_time, status, and message.
        """
        if self._mode == ETLMode.DRY_RUN:
            return

        async with self.session_ctx() as session:
            task: ETLRun = await session.get(ETLRun, run_id)
            task.rows_processed = rows_processed
            task.end_time = end_time
            task.status = status
            task.message = message
            await session.commit()

    def update_transaction_count(
        self, transaction_type: ETLOperation, table: str, count: int = 1
    ):
        """
        Increment the count for a given ETLOperation and table in the ETL status report.

        Args:
            transaction_type (ETLOperation): The ETL operation type (e.g., ETLOperation.INSERT, ETLOperation.UPDATE, ETLOperation.SKIP, ETLOperation.DELETE).
            table (str): Fully-qualified table name ('schema.table').
            count (int): Number of transactions to add to the total count. Default = 1.

        Raises:
            RuntimeError: If ETLStatusReport is not initialized.
        """
        self.__status_report.increment_transaction(transaction_type, table, count)

    def generate_checkpoint(self, line=None, record=None) -> ResumeCheckpoint:
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

    # -------------------------
    # Run orchestration
    # -------------------------

    async def run(
        self,
        runtime_params: Optional[Dict[str, Any]] = None,
    ) -> ProcessStatus:
        """
        Execute ETL.
        - mode=DRY_RUN (default): dry-run (no DB writes), count only.
        - mode=COMMIT: call load() with buffers/dataset, plugin commits internally.
        - mode=NON_COMMIT: call load() but plugin should roll back at the end.

        extra_params are merged atop validated self.params for this run only. The instance's original parameters are restored after the run.

        Returns:
            ProcessStatus: SUCCESS if ETL completed, FAIL otherwise.
        """
        merged_params = None
        run_id = None
        execution_status = None

        if runtime_params:
            merged = self._params.model_dump().copy()
            merged.update(runtime_params)
            merged_params = self.parameter_model()(**merged)
            self.logger.info(f"Runtime parameter overrides applied: {runtime_params}")
            self._params = merged_params
            self._commit_after = self._params.commit_after

        self.__start_time = datetime.now()

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
            run_id = await self.__db_log_plugin_run()
            execution_status = ProcessStatus.RUNNING
            self.__status_report = ETLStatusReport(
                status=execution_status,
                mode=self._mode,
                test=self._mode == ETLMode.DRY_RUN,
                run_id=run_id,
            )

        except Exception as e:
            self.logger.exception(f"Failed to initialize plugin: {e}")
            raise RuntimeError(f"Failed to initialize plugin: {e}")

        try:
            self.logger.log_plugin_configuration(self._params)
            self.logger.log_plugin_run()

            if self.load_strategy == LoadStrategy.CHUNKED:
                await self.__process_chunked_load()
            elif self.load_strategy == LoadStrategy.BULK:
                await self.__process_bulk_load()
            elif self.load_strategy == LoadStrategy.BATCH:
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
            if self._mode != ETLMode.DRY_RUN and run_id:
                await self.__db_update_plugin_task(
                    run_id,
                    datetime.now(),  # end time
                    execution_status,
                    message=f"ETL run failed: {e}",
                    rows_processed=self.__status_report.total_writes(),
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
            self.logger.status(self.__status_report)

            total_writes = self.__status_report.total_writes()

            if self._mode != ETLMode.DRY_RUN and total_writes == 0:
                self.logger.warning(
                    "WARNING: No transaction counts were updated in load(). "
                    "Implementers must call update_transaction_count for inserts/updates to ensure proper status reporting."
                )

            try:
                if self._mode != ETLMode.DRY_RUN:
                    await self.__db_update_plugin_task(
                        run_id,
                        end_time,
                        execution_status,
                        rows_processed=self.__status_report.total_writes(),
                    )
            except Exception as db_error:
                self.logger.exception(f"Failed to update plugin task in DB: {db_error}")

        return execution_status
