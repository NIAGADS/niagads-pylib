from enum import auto
from typing import Any, Dict, Optional

from niagads.common.types import ETLOperation, ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.types import ETLExecutionMode
from pydantic import BaseModel, Field, field_validator, model_validator

from niagads.utils.string import dict_to_info_string


class ResumeCheckpoint(BaseModel):
    """
    Resume checkpoint.
    - Use 'line' for source-relative resume (handled in extract()).
    - Use 'record' for domain resume (handled in extract() or load()).
    """

    line: Optional[int] = Field(
        None,
        description="Line number (1-based) to resume from; header not included in count",
    )
    record_id: Optional[str] = Field(
        None, description="Natural identifier or full record to resume from"
    )
    record: Optional[dict] = None

    @field_validator("record", mode="before")
    @classmethod
    def normalize_record(cls, v):
        if v is None or isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump()
        return v

    @model_validator(mode="after")
    def validate_checkpoint(self):
        if not self.line and not self.record_id and not self.record:
            raise ValueError(
                "Empty checkpoint, please specify line, record_id or record"
            )
        return self

    def as_info_string(self, debug: bool = False):
        if debug:  # debug -> return all not nulls
            values = self.model_dump(exclude_none=True)
        else:  # not debug, only include record if others are null
            if self.line is None and self.record_id is None:
                values = self.model_dump(exclude_none=True)
            else:
                values = self.model_dump(exclude_none=True, exclude=["record"])

        return dict_to_info_string(values)


class ETLRunStatus(BaseModel):
    """
    Status report for ETL operations.

    transactions: Dict mapping table names to operation counts.
        Format: {table_name: {operation: count}} or flat {table_name: count} for legacy.
    """

    transaction_record: Dict[str, Any] = None
    estimated_transaction_count: int = None
    operation: ETLOperation = None
    status: ProcessStatus
    mode: ETLExecutionMode
    commit: bool
    runtime: Optional[float] = None
    memory: Optional[float] = None
    task_id: Optional[int] = None
    run_id: Optional[int] = None

    def total_transactions(self):
        if self.transaction_record is None:
            if self.estimated_transaction_count is None:
                # when a developer exits during debugging on purpose, the status
                # will still be RUNNING
                if (
                    self.status is not ProcessStatus.FAIL
                    and self.status is not ProcessStatus.IN_PROGRESS
                ):
                    raise RuntimeError(
                        "Cannot calculate total writes - transaction tally not initialized"
                    )
                else:
                    return 0
            else:
                return self.estimated_transaction_count

        # expects {table: {op: count}}
        total = 0
        for value in self.transaction_record.values():
            # New format: per-operation counts
            total += sum(value.values())

        return total


class ETLLoadStrategy(CaseInsensitiveEnum):
    CHUNKED = auto()
    BULK = auto()
    BATCH = auto()
