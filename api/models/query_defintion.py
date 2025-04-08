
from typing import List, Optional, Type
from pydantic import BaseModel

from api.models.base_row_models import T_RowModel


class QueryDefinition(BaseModel):
    query: str
    countsQuery: Optional[str] = None
    # useIdCTE: bool = False # TODO: b/c difficult to insert w/out macro, maybe just explicitly write in the query as needed
    useIdSelectWrapper: bool = False
    bindParameters: Optional[List[str]] = None # bind parameter names
    fetchOne: bool = False # expect only one result, so return query result[0]
    errorOnNull: str = None # if not none will raise an error instead of returning empty
    messageOnResultSize: str = None
    
    def model_post_init(self, __context):
        if self.useIdSelectWrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            if self.bindParameters is not None:
                self.bindParameters.append('id')
            else:
                self.bindParameters = ['id']
        




