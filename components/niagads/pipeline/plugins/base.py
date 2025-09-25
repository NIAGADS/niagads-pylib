import uuid
import time
import psutil
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, List, Optional

from pydantic import BaseModel, Field
from etl_logging import ETLLogger
from models import BasePluginParams
from enums import ETLOperation  # your existing enum
from errors import ETLPluginError  # your existing error type
from niagads.database.session import DatabaseSessionManager  # async scoped session


class ResumeFrom(BaseModel):
    """
    Resume checkpoint.
    - Use 'line' for source-relative resume (handled in extract()).
    - Use 'id'   for domain resume (handled in transform()).
    """

    line: Optional[int] = Field(
        None, description="Line number (1-based) to resume from"
    )
    id: Optional[str] = Field(None, description="Natural identifier to resume from")

    @root_validator
    def require_line_or_id(cls, values):
        if not values.get("line") and not values.get("id"):
            raise ValueError("resume_from must define either 'line' or 'id'")
        return values


class BasePluginParams(BaseModel):
    """
    Base parameter model shared by all plugins.
    - commit_after controls streaming flush size (load called every N items).
    - log_file is the JSON log path for this plugin invocation.
    - resume_from hints are *interpreted by plugins* (extract/transform).
    Commit behavior is controlled by the pipeline/CLI via --commit.
    """

    commit_after: int = Field(
        10000, ge=1, description="Rows to buffer per load in streaming mode"
    )
    log_file: str = Field("etl.log", description="Path to JSON log file for the plugin")
    resume_from: Optional[ResumeFrom] = Field(None, description="Resume checkpoint")

    class Config:
        extra = "forbid"


class AbstractBasePlugin(ABC):
    """
    Abstract base class for ETL plugins (async).

    - Orchestrates ETL (extract -> transform -> load).
    - JSON logging only, with checkpoint logs discoverable by "message":"CHECKPOINT".
    - Dry-run by default; --commit flips to actual DB writes.
    - Resume:
        * extract() should honor resume_from.line (skip lines before that).
        * transform() may honor resume_from.id (skip until matching ID).
      These come from self.params['resume_from'] if provided.
    - Streaming vs Bulk is a class property (`streaming`).
      * streaming=True: records processed one-by-one and buffered; load() receives lists of size commit_after.
      * streaming=False: extract->transform over entire dataset; load() called once with bulk data.

    Plugins must implement `load()` using self.session_manager.session() (async).
    Plugins decide when to commit inside load() (per buffer/batch) — pipeline does NOT auto-commit.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        log_file: str = "etl.log",
        run_id: Optional[str] = None,
        settings: Any = None,
    ):
        self._name = name or self.__class__.__name__
        self._params: Dict[str, Any] = params or {}
        self._run_id = run_id or uuid.uuid4().hex[:12]  # short12 OK via hex slice
        self._row_count = 0
        self._start_time: Optional[float] = None

        # parameter model enforcement
        # allow subclasses to add fields via their own model; we validate here
        model: Type[BasePluginParams] = self.parameter_model()
        # accept provided params; forbid extras if model forbids
        self._params = model(**self._params).dict()

        # commit_after is read from validated params
        self._commit_after: int = self._params.get("commit_after", 10000)

        # logger (always JSON)
        self._logger = ETLLogger(
            name=self._name,
            log_file=self._params.get("log_file", "etl.log"),
            run_id=self._run_id,
            plugin=self._name,
        )

        # async DB session manager (scoped)
        self._session_manager = DatabaseSessionManager(settings=settings)

    # -------------------------
    # Abstract contract
    # -------------------------
    @classmethod
    @abstractmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        """
        Return the Pydantic parameter model for this plugin (must subclass BasePluginParams).
        """
        ...

    @property
    @abstractmethod
    def operation(self) -> ETLOperation:
        """
        Return the ETLOperation type used for rows created by this plugin run.
        """
        ...

    @property
    @abstractmethod
    def affected_tables(self) -> List[str]:
        """
        Return list of database tables this plugin writes to.
        """
        ...

    @property
    @abstractmethod
    def streaming(self) -> bool:
        """
        True if the plugin processes records line-by-line (streaming), False if bulk.
        """
        ...

    @abstractmethod
    def extract(self):
        """
        Extract parsed records.

        Resume behavior:
        - If self.params.get('resume_from', {}).get('line') is set, fast-forward
          the source to that line before yielding (plugins implement the logic).

        Return:
        - streaming=True: an iterator/generator yielding records
        - streaming=False: a dataset (list/iterable/dataframe) for bulk processing
        """
        ...

    @abstractmethod
    def transform(self, data):
        """
        Transform extracted data.

        Resume behavior:
        - If self.params.get('resume_from', {}).get('id') is set, you may return
          None for records until the matching ID is encountered; then return a
          transformed record thereafter.

        Return:
        - streaming=True: transformed single record or None (to skip)
        - streaming=False: transformed dataset (iterable/collection)
        """
        ...

    @abstractmethod
    async def load(self, transformed) -> int:
        """
        Persist transformed data using async SQLAlchemy session from:
            session = self.session_manager.session()
        Plugins must explicitly `await session.commit()` at safe points.

        Args:
            transformed: streaming - List[records] (buffer size <= commit_after)
                         bulk      - entire dataset

        Returns:
            int: number of rows persisted (or counted as would-be persisted in dry-run emulation)
        """
        ...

    # -------------------------
    # Run orchestration
    # -------------------------
    async def run(
        self, extra_params: Optional[Dict[str, Any]] = None, commit: bool = False
    ) -> bool:
        """
        Execute ETL.
        - commit=False (default): dry-run (no DB writes), count only.
        - commit=True: call load() with buffers/dataset, plugin commits internally.

        extra_params are merged atop validated self.params for this run only.
        """
        # merge runtime overrides (e.g., CLI resume_from)
        if extra_params:
            merged = self._params.copy()
            merged.update(extra_params)
            # re-validate merged params
            self._params = self.parameter_model()(**merged).dict()
            self._commit_after = self._params.get("commit_after", self._commit_after)

        self._row_count = 0
        buffer: list = []
        last_record = None
        last_line_no = 0
        ok = False

        try:
            self._start_time = time.time()

            if self.streaming:
                for last_line_no, rec in enumerate(self.extract(), start=1):
                    last_record = rec
                    transformed = self.transform(rec)
                    if transformed is None:
                        continue
                    buffer.append(transformed)
                    if len(buffer) >= self._commit_after:
                        if commit:
                            loaded = await self.load(buffer)
                            self._row_count += loaded
                        else:
                            self._row_count += len(buffer)
                        buffer.clear()
                # flush tail
                if buffer:
                    if commit:
                        loaded = await self.load(buffer)
                        self._row_count += loaded
                    else:
                        self._row_count += len(buffer)
                    buffer.clear()
            else:
                extracted = self.extract()
                transformed_bulk = self.transform(extracted)
                if commit:
                    loaded = await self.load(transformed_bulk)
                    self._row_count += loaded
                else:
                    if hasattr(transformed_bulk, "__len__"):
                        self._row_count = len(transformed_bulk)
                    else:
                        self._row_count = sum(1 for _ in transformed_bulk)

            # success log
            runtime = time.time() - self._start_time
            mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self._logger.status(
                "COMMIT" if commit else "DRY_RUN", self._row_count, runtime, mem_mb
            )
            ok = True

        except Exception as e:
            # checkpoint for resume (line + record snapshot)
            self._logger.checkpoint(
                line=last_line_no if self.streaming else -1, record=last_record, error=e
            )
            self._logger.exception(f"Plugin failed: {e}")
            ok = False

        return ok
