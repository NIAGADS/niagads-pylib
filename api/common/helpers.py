from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi import status
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Any, Dict

from api.common.enums import ResponseContent, CacheNamespace
from api.dependencies.parameters.services import InternalRequestParameters
from api.dependencies.parameters.optional import ResponseFormat
from api.models.base_models import BaseResponseModel, PaginationDataModel
from api.routers.redirect.common.constants import RedirectEndpoints

# basically allow creation of an arbitrary namespace
class Parameters(BaseModel):
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
class HelperParameters(BaseModel, arbitrary_types_allowed=True):
    internal: InternalRequestParameters
    model: Any
    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    pagination: PaginationDataModel = None
    parameters: Parameters = None
    
    # __pydantic_extra__: Dict[str, Any]  
    # model_config = ConfigDict(extra='allow')
    
    # from https://stackoverflow.com/a/67366461
    # allows ensurance taht model is always a child of BaseResponseModel
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, BaseResponseModel):
            return model
        raise RuntimeError(f'Wrong type for `model` : `{model}`; must be subclass of `BaseResponseModel`')
    
    @field_validator("content")
    def validate_content(cls, content):
        try:
            return ResponseContent(content)
        except NameError:
            raise RequestValidationError(f'Invalid value provided for `content`: {content}')


def __set_pagination(opts: HelperParameters, resultSize):
    if opts.model.is_paged():
        page = 1 if opts.pagination is None else opts.pagination.page
        nPages = getattr(opts.pagination, 'total_num_pages', 1)
        expectedResultSize = getattr(opts.pagination, 'total_num_records', resultSize)
        return PaginationDataModel(
            page=page, 
            total_num_pages= nPages, 
            paged_num_records=resultSize, 
            total_num_records=expectedResultSize
        )
    return None


async def generate_response(result: Any, opts:HelperParameters, isCached=False):
    if not isCached:
        response = None
        opts.internal.requestData.update_parameters(opts.parameters, exclude=['span', '_track'])
        if opts.model.is_paged():
            pagination: PaginationDataModel = __set_pagination(opts, len(result))
            response =  opts.model(request=opts.internal.requestData, pagination=pagination, response=result)
        else: 
            response = opts.model(request=opts.internal.requestData, response=result)
        # cache the response
        await opts.internal.internalCache.set(opts.internal.cacheKey.internal, response, namespace=opts.internal.cacheKey.namespace)
    else:
        response = result
        
    match opts.format:
        case ResponseFormat.TABLE:
            # cache the response again, this time by the requestId b/c 
            # the cacheKey cannot be passed through the URL  
            cacheKey = opts.internal.cacheKey.external   
            requestIsCached = await opts.internal.internalCache.exists(cacheKey, namespace=CacheNamespace.VIEW)
            if not requestIsCached:  # then cache it
                await opts.internal.internalCache.set(cacheKey, response, namespace=CacheNamespace.VIEW)
            
            redirectUrl = f'/redirect{RedirectEndpoints.TABLE.value}/{cacheKey}'
            return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
        case _:  
            return response

