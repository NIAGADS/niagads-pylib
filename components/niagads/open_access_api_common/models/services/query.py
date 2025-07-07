from typing import Any, List, Optional, Union
from niagads.open_access_api_common.models.records.core import Entity
from pydantic import BaseModel


class Filter(BaseModel):
    field: str
    value: Union[str, int, bool, float]


class QueryDefinition(BaseModel):
    query: Optional[str] = None
    countsQuery: Optional[str] = None
    useIdSelectWrapper: bool = False
    useFilterWrapper: bool = False
    filter: Filter = None
    bindParameters: Optional[List[str]] = None  # bind parameter names
    fetchOne: bool = False  # expect only one result, so return query result[0]
    # return specific jsonField from the full result
    jsonField: Optional[str] = None
    entity: Optional[Entity] = None

    def model_post_init(self, __context):
        if self.useIdSelectWrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            if self.bindParameters is not None:
                self.bindParameters.append("id")
            else:
                self.bindParameters = ["id"]
        if self.jsonField:
            self.query = "SELECT {field} FROM (" + self.query + ") q"
        if self.useFilterWrapper:
            self.query = (
                f"SELECT * FROM ({self.query}) q WHERE {self.filter.field} = [:filter]"
            )
