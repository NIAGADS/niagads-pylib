from fastapi import APIRouter, Depends, Path, Request

from api.common.enums import CacheNamespace, ResponseFormat
from api.common.exceptions import RESPONSES
from api.dependencies.parameters.services import InternalRequestParameters
from api.response_models.base_models import BaseResponseModel

from api.routers.view.common.constants import ROUTE_TAGS
from api.routers.view.dependencies.parameters import forwarding_request_param

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/table",
    tags=TAGS,
    responses=RESPONSES
)


tags = TAGS + ['Interactive Tables']
@router.get("/{forwardingRequestId}", tags=tags,
    name="Serialize and cache query response for a NIAGADS-viz-js Table")
async def get_table_view(
        request: Request,
        forwardingRequestId: str = Depends(forwarding_request_param),
        internal: InternalRequestParameters = Depends()
    ):
    
    cacheKey = forwardingRequestId + '_table_view'
    response = await internal.externalCache.get(cacheKey, namespace=CacheNamespace.VIEW)
    if response == None:    
        # original response store in internal cache
        requestResponse: BaseResponseModel = await internal.internalCache.get(forwardingRequestId, namespace=CacheNamespace.VIEW)
        response = requestResponse.to_view(ResponseFormat.TABLE)
        await internal.externalCache.set(cacheKey, response, namespace=CacheNamespace.VIEW)
        
    return response
        
        
