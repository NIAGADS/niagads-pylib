from pydantic import BaseModel, ConfigDict, Field


class TableRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    table_name: str
    schema_name: str
    table_id: int
    schema_id: int
    table_primary_key: str
