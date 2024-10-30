from fastapi import APIRouter, Depends, Path, Request

from api.common.enums import CacheNamespace, ResponseFormat
from api.common.exceptions import RESPONSES
from api.dependencies.parameters.services import InternalRequestParameters
from api.response_models.base_models import BaseResponseModel

from api.routers.redirect.dependencies.parameters import forwarding_request_param

from ..common.constants import ROUTE_TAGS


TAGS = ROUTE_TAGS + ["(Internal) Redirect JSON responses to Visualization Tools"]
router = APIRouter(
    prefix="/view",
    tags=TAGS,
    responses=RESPONSES
)


tags = TAGS + ['(Internal) Redirect Response to NIAGADS-viz-js Interactive Table']
@router.get("/table/{forwardingRequestId}", tags=tags,
    name="Serialize and cache query response for a NIAGADS-viz-js Table")
async def get_table_view(
        request: Request,
        forwardingRequestId: str = Depends(forwarding_request_param),
        internal: InternalRequestParameters = Depends()
    ):
    
    # check to see if redirect response is cached
    cacheKey = internal.cacheKey.external
    response = await internal.externalCache.get(cacheKey, namespace=CacheNamespace.VIEW)
    if response == None:    
        # original response store in internal cache
        requestResponse: BaseResponseModel = await internal.internalCache.get(forwardingRequestId, namespace=CacheNamespace.VIEW)
        response = requestResponse.to_view(ResponseFormat.TABLE, id=cacheKey)
        await internal.externalCache.set(cacheKey, response, namespace=CacheNamespace.VIEW)
        await internal.externalCache.set(f'{cacheKey}_request', requestResponse.request.model_dump(), namespace=CacheNamespace.VIEW)
        
        
    return response
        
        
