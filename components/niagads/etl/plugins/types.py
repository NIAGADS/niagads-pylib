from enum import auto
from typing import Dict, List, Optional, Type
from niagads.etl.plugins.parameters import BasePluginParams
from pydantic import BaseModel, Field, model_validator

from niagads.common.types import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.types import ETLMode

from sqlalchemy.orm import DeclarativeBase


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


class PluginMetadata(BaseModel):
    version: str
    description: str
    affected_tables: Optional[List[DeclarativeBase]] = []
    load_strategy: ETLLoadStrategy
    operation: ETLOperation
    is_large_dataset: bool = False
    parameter_model: Type[BasePluginParams]
