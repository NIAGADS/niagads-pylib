from pydantic import BaseModel
from fastapi import Depends, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from .constants import ROUTE_SESSION_MANAGER

class InternalServiceParameters(BaseModel, arbitrary_types_allowed=True):
    request: Request
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    