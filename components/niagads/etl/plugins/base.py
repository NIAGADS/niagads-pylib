import os
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

import psutil
from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.enums.common import ProcessStatus
from niagads.genomicsdb.models.admin.pipeline import ETLOperation, ETLOperationLog
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.config import ETLMode
from niagads.etl.plugins.logger import ETLLogger
from pydantic import BaseModel, Field, model_validator


class ResumeCheckpoint(BaseModel):
    """
    Resume checkpoint.
    - Use 'line' for source-relative resume (handled in extract()).
    - Use 'id'   for domain resume (handled in transform()).
    """

    line: Optional[int] = Field(
        None, description="Line number (1-based) to resume from"
    )
    id: Optional[str] = Field(None, description="Natural identifier to resume from")

    @model_validator(mode="after")
    def require_line_or_id(self):
        if not self.line and not self.id:
            raise ValueError("checkpoint must define either 'line' or 'id'")
        return self


class BasePluginParams(BaseModel):
    """
    Base parameter model for all ETL plugins.

    Attributes:
        commit_after (int): Number of records to buffer before each load/commit in streaming mode.
        log_file (str): Path to the JSON log file for this plugin invocation.
        checkpoint (Optional[ResumeFrom]): Resume checkpoint hints, interpreted by plugins (extract/transform).
        run_id (Optional[str]): Pipeline run identifier, provided by the pipeline.
        connection_string (Optional[str]): Database connection string, if needed.

    Note:
        Commit behavior is controlled by the pipeline/CLI via --commit. Plugins should not auto-commit unless instructed.
    """

    mode: ETLMode = Field(
        default=ETLMode.DRY_RUN, description=f"The ETL mode; one of {ETLMode.list()}"
    )
    commit_after: Optional[int] = Field(
        default=10000, ge=1, description="records to buffer per commit"
    )
    log_path: Optional[str] = Field(
        default=None,
        description="Path to JSON log file for the plugin.  If does not end in `.log`, assumes `log-path` is a directory and will write to `{log-path}/{plugin-name}.log",
    )
    resume_checkpoint: Optional[ResumeCheckpoint] = Field(
        default=None,
        description="resume checkpoint, a line number or record ID.  Indicate as line=<N> or id=<record ID>",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="optional run identifier, provided by pipeline manager when run in pipeline",
    )
    connection_string: Optional[str] = Field(
        default=None,
        description="database connection string; if not provided, the plugin will try to assign from `DATABASE_URI` property in an `.env` file",
    )
    verbose: Optional[bool] = Field(default=False, description="run in verbose mode")
    debug: Optional[bool] = Field(default=False, description="run in debug mode")

    # this shouldn't happen BTW b/c ge validator already set
    @model_validator(mode="after")
    def set_commit_after_none_if_zero(self):
        if self.commit_after == 0:
            self.commit_after = None
        return self


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
        self._run_id = self._params.run_id or uuid.uuid4().hex[:12]

        # logger (always JSON)
        self.logger: ETLLogger = ETLLogger(
            name=self._name,
            log_file=self._get_log_file_path(),
            run_id=self._run_id,
            plugin=self._name,
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

    async def _start_plugin_run_log(self) -> Optional[int]:
        """
        Log the start of a plugin run (except DRY_RUN). Returns the log row's ID, or None if not logged.
        """
        if self._mode == ETLMode.DRY_RUN:
            return None

        async with self._session_manager() as session:
            etl_log = ETLOperationLog(
                plugin_name=self._name,
                code_version=self.version,
                params=self._params.model_dump(),
                message=f"Started ETL run: mode={self._mode.value}",
                status=ProcessStatus.RUNNING.value,
                operation=self.operation.value,
                run_id=self._run_id,
                start_time=datetime.now(),
                end_time=None,
                rows_processed=0,
            )
            session.add(etl_log)
            await session.flush()
            etl_log_id = etl_log.etl_operation_log_id
            await session.commit()
        return etl_log_id

    async def _finalize_plugin_run_log(
        self,
        log_id: int,
        status: ProcessStatus,
        message: str,
        rows_processed: int,
    ):
        """
        Finalize the plugin run log with status, end time, and message.
        """
        async with self._session_manager() as session:
            etl_log = await session.get(ETLOperationLog, log_id)
            etl_log.status = status.value
            etl_log.end_time = datetime.now()
            etl_log.rows_processed = rows_processed
            etl_log.message = message
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
        orig_params = self._params
        orig_commit_after = self._commit_after
        merged_params = None
        task_id = None
        try:
            if runtime_params:
                merged = self._params.model_dump().copy()
                merged.update(runtime_params)
                merged_params = self.parameter_model()(**merged)
                self.logger.info(
                    f"Runtime parameter overrides applied: {runtime_params}"
                )
                self._params = merged_params
                self._commit_after = self._params.commit_after
            self.logger.info(
                f"Starting ETL run: mode={self._mode.value}, plugin={self._name}"
            )
            self._row_count = 0
            status = ProcessStatus.FAIL
            self._start_time = time.time()
            last_line_no = 0
            last_record = None

            # --- Log start of plugin run (except DRY_RUN) ---
            task_id = await self._start_plugin_run_log()

            # --- Log initialization status to file ---
            self.logger.init_status(
                plugin_name=self._name,
                params=self._params.model_dump(),
                run_id=self._run_id,
                task_id=task_id,
            )

            if self.streaming:
                last_line_no, last_record = await self._process_streaming_load()
            else:
                last_line_no, last_record = await self._process_bulk_load()
            # success log
            runtime = time.time() - self._start_time
            mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self.logger.status(
                self._mode.value.upper(), self._row_count, runtime, mem_mb
            )
            self.logger.flush()
            status = ProcessStatus.SUCCESS

            # --- Finalize plugin run log on success (except DRY_RUN) ---
            if self._mode != ETLMode.DRY_RUN and task_id:
                await self._finalize_plugin_run_log(
                    task_id,
                    status,
                    "ETL run completed successfully.",
                    self._row_count,
                )

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
            # Restore original params and commit_after
            self._params = orig_params
            self._commit_after = orig_commit_after
            return status
