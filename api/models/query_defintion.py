
from typing import List, Type
from pydantic import BaseModel

from api.models.base_row_models import T_RowModel

class QueryDefinition(BaseModel):
    name: str
    query: str
    useIdCTE: bool = False
    useIdSelectWrapper: bool = False
    resultType: Type[T_RowModel]
    bindParameters: List[str] # bind parameter names
    fetchOne: bool = False # expect only one result, so return result[0]
    errorOnNull: str = None # if not none will raise an error instead of returning empty

    # Developer NOTE: if fetchOne -> empty response = {}, else []
    
    def model_post_init(self, __context):
        if self.useIdCTE:
            self.query = "WITH (SELECT :id::text AS id) id, " + self.query
            self.bindParameters.insert(0, 'id')

        if self.useIdSelectWrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            self.bindParameters.append('id')
        




