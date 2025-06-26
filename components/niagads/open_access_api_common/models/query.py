from typing import Any, List, Optional
from niagads.open_access_api_common.models.core import Entity
from pydantic import BaseModel


class SQLQuery(BaseModel):
    bindParameters: Optional[List[str]] = None  # bind parameter names
    fetchOne: bool = False  # expect only one result, so return query result[0]
    jsonField: Optional[str] = (
        None  # if the SQL builds the JSON which field needs to be extracted & returned? see variant record for eg.
    )
    entity: Optional[Entity] = None


class Statement(SQLQuery):
    statement: Optional[Any] = None  # sql alchmey statement


class QueryDefinition(SQLQuery):
    query: Optional[str] = None
    countsQuery: Optional[str] = None
    useIdSelectWrapper: bool = False

    def model_post_init(self, __context):
        if self.useIdSelectWrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            if self.bindParameters is not None:
                self.bindParameters.append("id")
            else:
                self.bindParameters = ["id"]
