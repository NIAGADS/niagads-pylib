import os
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime

from niagads.utils.logging import FunctionContextAdapter
import psutil
from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.enums.common import ProcessStatus
from niagads.etl.config import ETLMode
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.logger import ETLLogger, ETLStatusReport
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.genomicsdb.models.admin.pipeline import ETLOperation, ETLTask

# TODO - fix handling of ETLStatus

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
        self._row_count = 0
        self._start_time: Optional[float] = None
        self._mode = self._params.mode

        # members initialized from validated params
        self._commit_after: int = self._params.commit_after
        self._run_id = self._params.run_id or uuid.uuid4().hex[:8].upper()

        self.logger: ETLLogger = FunctionContextAdapter(ETLLogger(
            name=self._name,
            log_file=self._get_log_file_path(),
            run_id=self._run_id,
            plugin=self._name,
            debug=self._debug,
        ))
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
    def streaming(self) -> bool:
        """
        Whether the plugin processes records line-by-line (streaming) or in bulk.

        Returns:
            bool: True if streaming, False if bulk.
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
    async def _flush_streaming_buffer(self, buffer, last_line_no):
        self.logger.info(
            f"Loading buffer of size {len(buffer)} at line {last_line_no} [mode={self._mode.value}]"
        )
        if self._mode != ETLMode.DRY_RUN:
            loaded = await self.load(buffer)
            self._row_count += loaded
        else:
            self._row_count += len(buffer)
        buffer.clear()

    async def _flush_bulk_batch(self, batch, last_line_no):
        if self._debug:
            self.logger.debug(
                f"Entering _flush_bulk_batch: batch size={len(batch)}, last_line_no={last_line_no}"
            )
        self.logger.info(
            f"Bulk loading batch of size {len(batch)} at record {last_line_no} [mode={self._mode.value}]"
        )
        if self._mode != ETLMode.DRY_RUN:
            loaded = await self.load(batch)
            self._row_count += loaded
        else:
            self._row_count += len(batch)
        batch.clear()

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

        for last_line_no, record in enumerate(self.extract(), start=1):
            if self._debug and self._verbose:
                self.logger.debug(
                    f"_process_streaming_load: Extracted record at line {last_line_no}: {record}"
                )
            last_record = record
            processed_record = self.transform(record)
            if self._debug and self._verbose:
                self.logger.debug(
                    f"_process_streaming_load: Transformed record at line {last_line_no}: {processed_record}"
                )
            buffer.append(processed_record)
            if len(buffer) >= self._commit_after:
                if self._debug and self._verbose:
                    self.logger.debug(
                        f"_process_streaming_load: Flushing buffer at line {last_line_no}, buffer size={len(buffer)}"
                    )
                await self._flush_streaming_buffer(buffer, last_line_no)

        # load residuals
        if buffer:
            if self._debug:
                self.logger.debug(
                    f"_process_streaming_load: Flushing final buffer at line {last_line_no}, buffer size={len(buffer)}"
                )
            await self._flush_streaming_buffer(buffer, last_line_no)

        return last_line_no, last_record

    async def _process_bulk_load(self):
        if self._debug:
            self.logger.debug("Entering _process_bulk_load")
        records = self.extract()
        processed_records = self.transform(records)
        last_record = None
        last_line_no = -1

        # If no batching, just load the whole dataset at once
        if not self._commit_after:
            if self._mode != ETLMode.DRY_RUN:
                await self.load(processed_records)

            if hasattr(processed_records, "__len__"):
                self._row_count = len(processed_records)
                last_record = processed_records[-1] if self._row_count > 0 else None
            else:  # get last record and row count from iterator
                count = 0
                last = None
                for last in processed_records:
                    count += 1
                self._row_count = count
                last_record = last

                last_line_no = self._row_count

        else:
            batch = []
            for last_line_no, last_record in enumerate(processed_records, start=1):
                batch.append(last_record)
                if len(batch) >= self._commit_after:
                    await self._flush_bulk_batch(batch, last_line_no)

            # load residuals
            if batch:
                await self._flush_bulk_batch(batch, last_line_no)

        return last_line_no, last_record

    async def _db_log_plugin_run(self) -> Optional[int]:
        """
        Log the start of a plugin run (except DRY_RUN). Returns the log row's ID, or None if not logged.
        """
        if self._mode == ETLMode.DRY_RUN:
            return None

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

    async def _db_update_plugin_task(self, task_id: int, rows_processed: int, end_time, status: ProcessStatus, message: str = None):
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
        
        if runtime_params:
            merged = self._params.model_dump().copy()
            merged.update(runtime_params)
            merged_params = self.parameter_model()(**merged)
            self.logger.info(
                f"Runtime parameter overrides applied: {runtime_params}"
            )
            self._params = merged_params
            self._commit_after = self._params.commit_after

        self._row_count = 0
        self._start_time = datetime.now()
        last_line_no = 0
        last_record = None
        
        try:
            task_id = await self._db_log_plugin_run()
            status = ETLStatusReport(
                skips=0,
                status=ProcessStatus.FAIL,
                mode=self._mode,
                test=(self._mode == ETLMode.DRY_RUN)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize plugin: {e}")
    
        try:
            self.logger.log_plugin_configuration(self._params)

            if self.streaming:
                last_line_no, last_record = await self._process_streaming_load()
            else:
                last_line_no, last_record = await self._process_bulk_load()

        except Exception as e:
            # checkpoint for resume (line + record snapshot)

            checkpoint_kwargs = {
                "line": last_line_no if self.streaming else -1,
                "error": e,
            }
            if last_record is not None:
                if self._verbose or self._debug:
                    checkpoint_kwargs["record"] = last_record
                record_id = self.get_record_id(last_record)
                if record_id is not None:
                    checkpoint_kwargs["record_id"] = record_id
            self.logger.checkpoint(**checkpoint_kwargs)
            self.logger.exception(f"Plugin failed: {e}")
            status = ProcessStatus.FAIL

            # --- Finalize plugin run log on error (except DRY_RUN) ---
            if self._mode != ETLMode.DRY_RUN and task_id:
                await self._finalize_plugin_run_log(
                    task_id,
                    status,
                    f"ETL run failed: {e}",
                    self._row_count,
                )
        finally:
            # log status
            end_time = datetime.now()
            runtime = (end_time - self._start_time).total_seconds()
            mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self.logger.status(
                ETLStatusReport(
                    task_id=task_id,
                    updates=None,
                    inserts=None,
                    skips=0,
                    status=status.status if hasattr(status, 'status') else status,
                    mode=self._mode,
                    test=(self._mode == ETLMode.DRY_RUN),
                    runtime=runtime,
                    memory=mem_mb,
                )
            )
            
            try:
                if task_id is not None: await self._db_update_plugin_task(task_id, self._row_count, end_time)
            except Exception as db_error:
                self.logger.exception(f"Failed to update plugin task in DB: {db_error}")

        return status



