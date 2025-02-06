from fastapi import APIRouter, Depends, Path, Request

from api.common.enums import CacheKeyQualifier, CacheNamespace, RedirectEndpoint, ResponseView
from api.common.exceptions import RESPONSES
from api.dependencies.parameters.services import InternalRequestParameters

from api.models.base_response_models import BaseResponseModel
from api.routers.redirect.dependencies.parameters import forwarding_request_param


TAGS = ["(Internal) Redirect JSON responses to Visualization Tools"]
router = APIRouter(
    prefix="/view",
    tags=TAGS,
    responses=RESPONSES
)


tags = ['(Internal) Redirect Response to NIAGADS-viz-js Interactive Table']
@router.get("/table/{forwardingRequestId}", tags=tags,
    name="Serialize and cache query response for a NIAGADS-viz-js Table")
async def get_table_view(
        request: Request,
        forwardingRequestId: str = Depends(forwarding_request_param),
        internal: InternalRequestParameters = Depends()
    ):
    
    # check to see if redirect response is cached
    cacheKey = internal.cacheKey.encrypt()
    originatingResponse: BaseResponseModel = await internal.internalCache.get(forwardingRequestId, namespace=CacheNamespace.VIEW)
    viewResponse = await internal.externalCache.get(cacheKey, namespace=CacheNamespace.VIEW)
    if viewResponse == None:    
        # original response store in internal cache
        viewResponse = originatingResponse.to_view(ResponseView.TABLE, id=cacheKey)
        await internal.externalCache.set(cacheKey, viewResponse, namespace=CacheNamespace.VIEW)
        
    # need to save originating response and pagination information for 
    originatingRequestDetails = originatingResponse.request.model_dump(exclude=['request_id']) 
    pagination = getattr(originatingResponse, 'pagination', None)
    if pagination is not None:
        originatingRequestDetails.update({'pagination': originatingResponse.pagination.model_dump()})    
    originatingRequestDetails.update({'query_id' : cacheKey, 'redirect_to': RedirectEndpoint.TABLE })
    await internal.externalCache.set(f'{cacheKey}{CacheKeyQualifier.REQUEST_PARAMETERS}', 
        originatingRequestDetails, namespace=CacheNamespace.VIEW)

    return viewResponse
        
        
