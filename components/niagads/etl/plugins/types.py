from enum import auto
from typing import Dict, Optional
from pydantic import BaseModel

from niagads.common.types import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.plugins.parameters import ResumeCheckpoint
from niagads.etl.types import ETLMode


class ETLLoadResult(BaseModel):
    checkpoint: Optional[ResumeCheckpoint] = None
    transaction_count: int


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
    """

    transactions: Dict[str, int] = None
    estimated_transaction_count: int = None
    operation: ETLOperation = None
    status: ProcessStatus
    mode: ETLMode
    runtime: Optional[float] = None
    memory: Optional[float] = None
    task_id: Optional[int] = None
    run_id: Optional[int] = None

    def total_writes(self):
        if self.transactions is None:
            if self.estimated_transaction_count is None:
                raise RuntimeError(
                    "Cannot calculate total writes - transaction tally not initialized"
                )
            else:
                return self.estimated_transaction_count

        return sum(self.transactions.values())


class ETLLoadStrategy(CaseInsensitiveEnum):
    CHUNKED = auto()
    BULK = auto()
    BATCH = auto()
