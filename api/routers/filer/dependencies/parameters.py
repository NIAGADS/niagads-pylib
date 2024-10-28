from fastapi import Depends, Path, Query
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from api.common.formatters import clean
from api.dependencies.database import DatabaseSessionManager
from api.dependencies.parameters.services import InternalRequestParameters as BaseInternalRequestParameters

from ..common.constants import ROUTE_DATABASE

# override session to use the ROUTE_SESSION_MANAGER
ROUTE_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)
class InternalRequestParameters(BaseInternalRequestParameters, arbitrary_types_allowed=True):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]

async def path_track_id(track: str = Path(description="FILER track identifier")) -> str:
    return clean(track)

async def query_track_id(track: str = Query(description="comma separated list of one or more FILER track identifiers")) -> str:
    return clean(track)