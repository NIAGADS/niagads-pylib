from pydantic import BaseModel
from fastapi import Depends, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import DatabaseSessionManager
from api.dependencies.parameters.services import InternalRequestParameters as BaseInternalRequestParameters

from ..common.constants import ROUTE_DATABASE

ROUTE_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)

# override session to use the ROUTE_SESSION_MANAGER
class InternalRequestParameters(BaseInternalRequestParameters, arbitrary_types_allowed=True):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    