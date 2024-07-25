from pydantic import BaseModel
from typing import Optional
from fastapi import Query

# TODO: common params: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/

# Query(Query()) nesting has to do w/FAST-API bug for documentation of Depends() params
# see https://github.com/tiangolo/fastapi/issues/4700
class OptionalParams(BaseModel):
    limit: Optional[int] = Query(Query(default=50, description="maximum number of results to return; please not pagination is not yet implemented"))
    page: Optional[int] = Query(Query(default=None, description="current page; not yet implemented - pagination coming soon"))
    countOnly: Optional[bool] = Query(Query(default = False, description="return result size (count) only"))
    idsOnly: Optional[bool] = Query(Query(default = False, description="return only the IDS (no annotation or metadata) for matching records"))