from typing import Type
from niagads.database.genomicsdb.schema.mixins import GenomicsDBTableMixin
from pydantic import BaseModel, ConfigDict, Field


# allow arbitrary types to support ORM table class
class TableRef(BaseModel, arbitrary_types_allowed=True):
    """
    A table reference object; helper to leverage table catalog
    """

    model_config = ConfigDict(from_attributes=True)
    table_name: str = Field(..., title="Table Name", description="Name of the table.")
    schema_name: str = Field(
        ..., title="Schema Name", description="Name of the schema containing the table."
    )
    table_id: int = Field(
        ..., title="Table ID", description="Unique identifier for the table."
    )
    schema_id: int = Field(
        ..., title="Schema ID", description="Unique identifier for the schema."
    )
    table_primary_key: str = Field(
        ...,
        title="Table Primary Key",
        description="Name of the primary key column for the table.",
    )
    table_stable_id: str = (Field(default=None, title="Table Stable (FAIR) ID"),)
    table_class: Type[GenomicsDBTableMixin] = Field(
        ..., title="Table ORM Class", description="ORM class for the table."
    )
