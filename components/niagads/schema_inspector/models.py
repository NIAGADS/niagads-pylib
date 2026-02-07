"""Pydantic models for schema inspector request/response data"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class InspectionRequest(BaseModel):
    """Request model for table inspection"""

    schema_name: str = Field(..., description="Name of the database schema")
    table_name: str = Field(..., description="Name of the table to inspect")
    run_id: Optional[int] = Field(None, description="ETL run ID to filter by")

    @field_validator("schema_name", "table_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace from string fields"""
        return v.strip() if v else v


class InspectionResponse(BaseModel):
    """Response model for table inspection results"""

    schema: str = Field(..., description="Schema name")
    table: str = Field(..., description="Table name")
    run_id: Optional[int] = Field(None, description="Filter run_id used")
    row_count: int = Field(..., description="Number of rows returned")
    total_rows: int = Field(..., description="Total rows in table (if available)")
    columns: List[str] = Field(..., description="List of column names")
    rows: List[Dict[str, Any]] = Field(..., description="List of row data")
    has_more: bool = Field(
        ..., description="Indicates if there are more rows beyond the limit"
    )
    limit: int = Field(default=1000, description="Row limit applied to query")


class SchemaInfo(BaseModel):
    """Information about available schemas and tables"""

    schemas: Dict[str, List[str]] = Field(
        ..., description="Dictionary mapping schema names to table lists"
    )


class TableInfo(BaseModel):
    """Detailed information about a specific table"""

    schema: str = Field(..., description="Schema name")
    table: str = Field(..., description="Table name")
    columns: List[str] = Field(..., description="List of column names")
    has_run_id: bool = Field(..., description="Indicates if table has run_id column")
