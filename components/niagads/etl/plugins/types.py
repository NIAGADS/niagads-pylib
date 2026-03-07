from enum import auto
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field, model_validator

from niagads.common.types import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.types import ETLMode


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
    record: Optional[str] = Field(
        None, description="Natural identifier or full record to resume from"
    )
    full_record: Optional[dict]

    @model_validator(mode="after")
    def validate_checkpoint(self):
        if not self.line and not self.record:
            raise ValueError("checkpoint must define either 'line' or 'record'")
        return self


class ETLOperation(CaseInsensitiveEnum):
    """
    Type of ETL operation:
    - LOAD: Insert new or Update existing records.
    - UPDATE: Update existing records.
    - DELETE: Delete records.
    - INSERT: Insert new records.
    """

    INSERT = auto()
    UPDATE = auto()
    LOAD = auto()
    DELETE = auto()


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
    mode: ETLMode
    runtime: Optional[float] = None
    memory: Optional[float] = None
    task_id: Optional[int] = None
    run_id: Optional[int] = None

    def total_transactions(self):
        if self.transaction_record is None:
            if self.estimated_transaction_count is None:
                raise RuntimeError(
                    "Cannot calculate total writes - transaction tally not initialized"
                )
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
