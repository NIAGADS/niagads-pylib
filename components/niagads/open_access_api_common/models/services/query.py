from typing import Any, List, Optional, Union
from niagads.open_access_api_common.models.records.core import Entity
from pydantic import BaseModel


class QueryFilter(BaseModel):
    field: str
    value: Union[str, int, bool, float]
    operator: str


class QueryDefinition(BaseModel):
    query: Optional[str] = None
    countsQuery: Optional[str] = None

    useIdSelectWrapper: bool = False
    allowFilters: bool = False  # if filter param is present, add filter wrapper
    fetchOne: bool = False  # always return exactly one result
    jsonField: Optional[str] = None  # only return specific field, can be dynamic
    bindParameters: Optional[List[str]] = None  # bind parameter names

    entity: Optional[Entity] = None  # for messaging

    def model_post_init(self, __context):
        if self.useIdSelectWrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            if self.bindParameters is not None:
                self.bindParameters.append("id")
            else:
                self.bindParameters = ["id"]
        if self.jsonField:
            self.query = "SELECT {field} FROM (" + self.query + ") q"

    def get_filter_query(self, filter: QueryFilter):
        # do not fill in filter.value; leave for prepared statement using the bind parameter for security
        return f"SELECT * FROM ({self.query}) q WHERE {filter.field} {filter.operator} :filter"
