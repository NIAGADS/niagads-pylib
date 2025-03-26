from fastapi import Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import DatabaseSessionManager
from api.dependencies.parameters.services import InternalRequestParameters as BaseInternalRequestParameters

from api.routes.genomics.common.constants import ROUTE_DATABASE, METADATA_DATABASE

# initialize database and api wrapper session managers; this allows us to 
# use connection pooling
TRACK_DATA_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)
METADATA_SESSION_MANAGER = DatabaseSessionManager(METADATA_DATABASE)
class InternalRequestParameters(BaseInternalRequestParameters, arbitrary_types_allowed=True):
    session: Annotated[AsyncSession, Depends(TRACK_DATA_SESSION_MANAGER)]
    metadataSession: Annotated[AsyncSession, Depends(METADATA_SESSION_MANAGER)]
