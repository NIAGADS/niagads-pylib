from fastapi import Depends, Path, Query
from typing import Annotated, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from api.config.settings import get_settings
from api.common.enums import ResponseFormat
from api.common.formatters import clean, print_enum_values
from api.dependencies.database import DatabaseSessionManager
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.services import InternalRequestParameters as BaseInternalRequestParameters

from ..common.constants import ROUTE_DATABASE, TRACK_SEARCH_FILTER_FIELD_MAP

# initialize database and api wrapper session managers; this allows us to 
# use connection pooling
ROUTE_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)
class InternalRequestParameters(BaseInternalRequestParameters, arbitrary_types_allowed=True):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]

"""
async def path_track_id(track: str = Path(description="FILER track identifier")) -> str:
    return clean(track)

async def query_collection_name(collection: Optional[str] = Query(default=None, description="FILER collection name")) -> str:
    return clean(collection)

async def path_collection_name(collection: str = Path(description="FILER collection name")) -> str:
    return clean(collection)

async def required_query_track_id(track: str = Query(description="comma separated list of one or more FILER track identifiers")) -> str:
    return clean(track)

async def optional_query_track_id(track: Optional[str] = Query(default=None, description="comma separated list of one or more FILER track identifiers")) -> str:
    return clean(track)

METADATA_FILTER_PARAM = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
"""