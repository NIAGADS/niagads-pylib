from pydantic import BaseModel
from typing import Optional
from fastapi import Query

# TODO: common params: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/

# Query(Query()) nesting has to do w/FAST-API bug for documentation of Depends() params
# see https://github.com/tiangolo/fastapi/issues/4700

class OptionalParams(BaseModel):
    limit: Optional[int] = Query(Query(default=None, description="maximum number of results to return; please note that `pagination is not yet implemented`"))
    page: Optional[int] = Query(Query(default=None, description="current page; please note that `pagination is not yet implemented`"))
    countOnly: Optional[bool] = Query(Query(default = False, description="return result size (count) only"))

class ExtendedOptionalParams(OptionalParams):
    idsOnly: Optional[bool] = Query(Query(default = False, description="return only the IDS (no annotation or metadata) for matching records"))

class TrackResponseTyeParams(BaseModel):
    browserSession: Optional[bool] = Query(Query(default=False, description="return NIAGADS Genome Browser Session JSON"))
    browser: Optional[bool] = Query(Query(default=False, description="return NIAGADS Genome Browser"))
    table: Optional[bool] = Query(Query(default=False, description="return interactive table of query results"))