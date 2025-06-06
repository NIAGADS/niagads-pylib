from typing import List, Optional
from pydantic import BaseModel


class QueryDefinition(BaseModel):
    query: str
    countsQuery: Optional[str] = None
    useIdSelectWrapper: bool = False
    bindParameters: Optional[List[str]] = None  # bind parameter names
    fetchOne: bool = False  # expect only one result, so return query result[0]
    errorOnNull: str = (
        None  # if not none will raise an error instead of returning empty
    )
    messageOnResultSize: str = None

    def model_post_init(self, __context):
        if self.useIdSelectWrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            if self.bindParameters is not None:
                self.bindParameters.append("id")
            else:
                self.bindParameters = ["id"]
