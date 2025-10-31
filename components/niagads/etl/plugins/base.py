from collections import deque
from enum import auto
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from niagads.enums.core import CaseInsensitiveEnum
import psutil
from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.enums.common import ProcessStatus
from niagads.etl.config import ETLMode
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.logger import ETLLogger, ETLStatusReport, ETLTransactionCounter
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.genomicsdb.models.admin.pipeline import ETLOperation, ETLTask
from niagads.utils.logging import FunctionContextLoggerWrapper


class LoadStrategy(CaseInsensitiveEnum):
    STREAMING = auto()
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
    - Streaming vs Bulk is a class property (`streaming`).
        * streaming=True: records processed one-by-one and buffered; load() receives lists of size commit_after.
        * streaming=False: extract->transform over entire dataset; load() called once with bulk data.

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
        self._written_record_count = 0
        self._start_time: Optional[float] = None
        self._mode = self._params.mode
        self._status_report: ETLStatusReport = None

        # members initialized from validated params
        self._commit_after: int = self._params.commit_after
        self._run_id = self._params.run_id or uuid.uuid4().hex[:8].upper()

        self.logger: ETLLogger = FunctionContextLoggerWrapper(
            ETLLogger(
                name=self._name,
                log_file=self._get_log_file_path(),
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
            self._session_manager = DatabaseSessionManager(
                connection_string=self._connection_string, echo=self._debug
            )
        else:
            self._session_manager = None

    @property
    def status_report(self):
        return self._status_report

    def _get_log_file_path(self):
        # if no path specified, just return
        # standardized log file name
        # will write to cwd
        if not self._params.log_path:
            return f"{self._name}.log"

        # otherwise if a .log file specified, write to that file
        if ".log" in self._params.log_path:
            return self._params.log_path

        # otherwise assume log_path is a directory
        # and write to standardize log file name in that path
        return os.path.join(self._params.log_path, f"{self._name}.log")

    def update_transaction_count(
        self, transaction_type: ETLTransactionCounter, table: str, count: int = 1
    ):
        """
        Increment an ETL transaction type (insert, update, skip) by 1.

        Args:
            transaction_type (ETLTransactionCounter): Transaction type ('inserts', 'updates', 'skips').
            table (str): Fully-qualified table name ('schema.table').
            count (int): number of transactions to add to the total count. Default = 1.

        Raises:
            RuntimeError: If ETLStatusReport is missing the expected increment method.
        """
        method = f"increment_{ETLTransactionCounter(transaction_type).value.lower()}s"
        incrementer = getattr(self._status_report, method, None)
        if not callable(incrementer):
            raise RuntimeError(f"ETLStatusReport missing expected method {method}")
        incrementer(table, count)

    async def _handle_transaction(self, session, residuals: bool = False) -> None:
        """
        Commit or rollback the session based on ETLMode and commit_after logic.
        """
        total_transactions = self._status_report.total_writes()
        if residuals or (
            self._commit_after and total_transactions >= self._commit_after
        ):
            if self._mode == ETLMode.COMMIT:
                await session.commit()
            elif self._mode == ETLMode.NON_COMMIT:
                await session.rollback()

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
        Whether the plugin processes records line-by-line (streaming),  in bulk, or in batch.

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
    async def load(self, transformed) -> int:
        """
        Persist transformed data using an async SQLAlchemy session.

        IMPLEMENTER WARNING:
        You MUST tally all updates and inserts using self.update_transaction_count
        for every record processed in your load() implementation. This is required
        for accurate ETL status reporting.

        Args:
            transformed: The data to persist. For streaming, a list of records (buffer size <= commit_after). For bulk, the entire dataset.

        Returns:
            int: Number of rows persisted (or counted as would-be persisted in dry-run emulation).
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

    @property
    def version(self):
        # Local import to avoid circular import
        from niagads.etl.plugins.registry import PluginRegistry

        return PluginRegistry.describe(self.__class__.__name__).get("version")

    # -------------------------
    # Run orchestration
    # -------------------------
    async def _process_streaming_load(self):
        if self._debug:
            self.logger.debug("Entering _process_streaming_load")
        if self._commit_after is None:
            raise RuntimeError(
                "Streaming load requires commit_after to be set to a value >= 1."
            )

        buffer: list = []
        last_record = None
        last_line_no = 0

        async with self._session_manager() as session:
            for last_line_no, record in enumerate(self.extract(), start=1):
                if self._debug and self._verbose:
                    self.logger.debug(
                        f"Extracted record at line {last_line_no}: {record}"
                    )
                last_record = record
                processed_record = self.transform(record)
                if self._debug and self._verbose:
                    self.logger.debug(
                        f"Transformed record at line {last_line_no}: {processed_record}"
                    )
                buffer.append(processed_record)
                if len(buffer) >= self._commit_after:
                    if self._debug and self._verbose:
                        self.logger.debug(
                            f"Flushing buffer at line {last_line_no}, buffer size={len(buffer)}"
                        )
                    await self._flush_streaming_buffer(buffer, last_line_no, session)
                    await self._handle_transaction(session, residuals=False)

            # load residuals
            if buffer:
                if self._debug:
                    self.logger.debug(
                        f"Flushing final buffer at line {last_line_no}, buffer size={len(buffer)}"
                    )
                await self._flush_streaming_buffer(buffer, last_line_no, session)
                await self._handle_transaction(session, residuals=True)

        return last_line_no, last_record

    async def _load(self, data, session):
        """
        Loads data and checks if transaction counts (writes + skips) increased.
        Raises RuntimeError if no change is detected after load().
        """
        pre_count = (
            self._status_report.total_writes() + self._status_report.total_skips()
        )
        await self.load(data, session)
        post_count = (
            self._status_report.total_writes() + self._status_report.total_skips()
        )
        if post_count == pre_count:
            msg = f"No transaction counts were updated in load(). "
            msg += "Implementers must call update_transaction_count for inserts/updates/skips."
            raise RuntimeError(msg)

    async def _flush_streaming_buffer(self, buffer, last_line_no, session):
        if self._debug:
            self.logger.debug(
                f"Loading buffer of size {len(buffer)} at line {last_line_no} [mode={self._mode.value}]"
            )
        if self._mode == ETLMode.DRY_RUN:
            table = (
                self.affected_tables[0] if len(self.affected_tables) == 1 else "DRY.RUN"
            )
            self.update_transaction_count(
                ETLTransactionCounter.INSERT, table, len(buffer)
            )
        else:
            await self._load(buffer, session)
        buffer.clear()

    async def _process_bulk_load(self):
        if self._debug:
            self.logger.debug("Entering _process_bulk_load")
        records = self.extract()
        processed_records = self.transform(records)
        last_record = None
        last_line_no = -1

        async with self._session_manager() as session:
            # Bulk: load all at once, ignore commit_after
            if self._mode == ETLMode.DRY_RUN:
                table = (
                    self.affected_tables[0]
                    if len(self.affected_tables) == 1
                    else "DRY.RUN"
                )
                try:
                    count = len(processed_records)
                except TypeError:
                    count = sum(1 for _ in processed_records)
                self.update_transaction_count(
                    ETLTransactionCounter.INSERT, table, count
                )
            else:
                await self._load(processed_records, session)
                await self._handle_transaction(session, residuals=True)

        # FIXME: we are not handling identifying the last processed record/line
        # correctly for iterators which may no longer exist by this point.
        # question -> will we allow iterators for bulk/batch loads?
        if hasattr(processed_records, "__len__") and processed_records:
            last_record = processed_records[-1]
            last_line_no = len(processed_records)
        else:
            try:
                last_record = deque(processed_records, maxlen=1)[0]
            except Exception:
                last_record = None
            last_line_no = -1

        return last_line_no, last_record

    async def _process_bulk_in_batch_load(self):
        if self._debug:
            self.logger.debug("Entering _process_bulk_in_batch_load")
        records = self.extract()
        processed_records = self.transform(records)
        batch = []
        last_record = None
        last_line_no = 0

        async with self._session_manager() as session:
            for last_line_no, record in enumerate(processed_records, start=1):
                batch.append(record)
                last_record = record
                if len(batch) >= self._commit_after:
                    await self._flush_bulk_batch(batch, last_line_no, session)
                    await self._handle_transaction(session, residuals=False)
            if batch:  # residuals
                await self._flush_bulk_batch(batch, last_line_no, session)
                await self._handle_transaction(session, residuals=True)

        return last_line_no, last_record

    async def _flush_bulk_batch(self, batch, last_line_no, session):
        if self._debug:
            self.logger.info(
                f"Bulk loading batch of size {len(batch)} at record {last_line_no} [mode={self._mode.value}]"
            )
        if self._mode == ETLMode.DRY_RUN:
            table = (
                self.affected_tables[0] if len(self.affected_tables) == 1 else "DRY.RUN"
            )
            self.update_transaction_count(
                ETLTransactionCounter.INSERT, table, len(batch)
            )
        else:
            await self._load(batch, session)
        batch.clear()

    async def _db_log_plugin_run(self) -> Optional[int]:
        """
        Log the start of a plugin run (except DRY_RUN). Returns the log row's ID, or None if not logged.
        """
        if self._mode == ETLMode.DRY_RUN:
            return ETLMode.DRY_RUN

        async with self._session_manager() as session:
            task = ETLTask(
                plugin_name=self._name,
                code_version=self.version,
                params=self._params.model_dump(),
                message="plugin run initiated",
                status=ProcessStatus.RUNNING,
                operation=self.operation.value,
                run_id=self._run_id,
                start_time=self._start_time,
                rows_processed=0,
            )
            session.add(task)
            await session.commit()
        return task.task_id

    async def _db_update_plugin_task(
        self,
        task_id: int,
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
        async with self._session_manager() as session:
            task: ETLTask = await session.get(ETLTask, task_id)
            task.rows_processed = rows_processed
            task.end_time = end_time
            task.status = status
            task.message = message
            await session.commit()

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
        task_id = None
        execution_status = None

        if runtime_params:
            merged = self._params.model_dump().copy()
            merged.update(runtime_params)
            merged_params = self.parameter_model()(**merged)
            self.logger.info(f"Runtime parameter overrides applied: {runtime_params}")
            self._params = merged_params
            self._commit_after = self._params.commit_after

        self._written_record_count = 0
        self._start_time = datetime.now()
        last_line_no = 0
        last_record = None

        try:
            task_id = await self._db_log_plugin_run()
            execution_status = ProcessStatus.RUNNING
            self._status_report = ETLStatusReport(
                status=execution_status,
                mode=self._mode,
                test=self._mode == ETLMode.DRY_RUN,
                task_id=task_id,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize plugin: {e}")

        try:
            self.logger.log_plugin_configuration(self._params)
            self.logger.log_plugin_run()

            if self.load_strategy == LoadStrategy.STREAMING:
                last_line_no, last_record = await self._process_streaming_load()
            elif self.load_strategy == LoadStrategy.BULK:
                last_line_no, last_record = await self._process_bulk_load()
            elif self.load_strategy == LoadStrategy.BATCH:
                last_line_no, last_record = await self._process_bulk_in_batch_load()
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
            if self.load_strategy == LoadStrategy.STREAMING:
                checkpoint_kwargs["line"] = last_line_no
            if last_record is not None:
                if self._verbose or self._debug:
                    checkpoint_kwargs["record"] = last_record
                record_id = self.get_record_id(last_record)
                if record_id is not None:
                    checkpoint_kwargs["record_id"] = record_id
            self.logger.checkpoint(**checkpoint_kwargs)
            self.logger.exception(f"Plugin failed: {e}")

            # --- Finalize plugin run log on error (except DRY_RUN) ---
            if self._mode != ETLMode.DRY_RUN and task_id:
                await self._db_update_plugin_task(
                    task_id,
                    datetime.now(),  # end time
                    execution_status,
                    message=f"ETL run failed: {e}",
                    rows_processed=self._status_report.total_writes(),
                )
        finally:
            # log status
            end_time = datetime.now()
            runtime = (end_time - self._start_time).total_seconds()
            mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self._status_report.runtime = runtime
            self._status_report.memory = mem_mb
            self._status_report.status = execution_status
            self.logger.status(self._status_report)
            total_writes = self._status_report.total_writes()

            if self._mode != ETLMode.DRY_RUN and total_writes == 0:
                self.logger.warning(
                    "WARNING: No transaction counts were updated in load(). "
                    "Implementers must call update_transaction_count for inserts/updates to ensure proper status reporting."
                )

            try:
                if self._mode != ETLMode.DRY_RUN:
                    await self._db_update_plugin_task(
                        task_id,
                        end_time,
                        execution_status,
                        rows_processed=self._status_report.total_writes(),
                    )
            except Exception as db_error:
                self.logger.exception(f"Failed to update plugin task in DB: {db_error}")

        return execution_status
