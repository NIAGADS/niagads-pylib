from fastapi import APIRouter, Depends, Path, Request

from api.common.enums import CacheNamespace, ResponseFormat
from api.common.exceptions import RESPONSES
from api.dependencies.parameters.services import InternalRequestParameters

from api.models.base_response_models import BaseResponseModel
from api.routers.redirect.dependencies.parameters import forwarding_request_param

from ..common.constants import ROUTE_TAGS, RedirectEndpoints


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
    cacheKey = internal.cacheKey.external
    response = await internal.externalCache.get(cacheKey, namespace=CacheNamespace.VIEW)
    if response == None:    
        # original response store in internal cache
        originatingResponse: BaseResponseModel = await internal.internalCache.get(forwardingRequestId, namespace=CacheNamespace.VIEW)
        response = originatingResponse.to_view(ResponseFormat.TABLE, id=cacheKey)
        await internal.externalCache.set(cacheKey, response, namespace=CacheNamespace.VIEW)
        
        # need to save response and pagination information
        originatingRequestDetails = originatingResponse.request.model_dump(exclude=['request_id', 'msg'])
        pagination = getattr(originatingResponse, 'pagination', None)
        if pagination is not None:
            originatingRequestDetails.update({'pagination': originatingResponse.pagination.model_dump()})
        await internal.externalCache.set(f'{cacheKey}_request', originatingRequestDetails, namespace=CacheNamespace.VIEW)
    
    return {'queryId' : cacheKey, 'redirect': RedirectEndpoints.TABLE }
        
        
