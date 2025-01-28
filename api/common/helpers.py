from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi import Response, status
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Any, Dict

from api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from api.common.enums import ResponseContent, CacheNamespace
from api.common.types import Range

from api.dependencies.parameters.services import InternalRequestParameters
from api.dependencies.parameters.optional import ResponseFormat
from api.models.base_models import PaginationDataModel
from api.models.base_response_models import BaseResponseModel
from api.models.igvbrowser import IGVBrowserTrackSelecterResponse
from api.routers.redirect.common.constants import RedirectEndpoints

INTERNAL_PARAMETERS = ['span', '_paged_tracks']

class Parameters(BaseModel):
    """ arbitrary namespace to store request parameters and pass them to helpers """
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
    def get(self, attribute:str, default: Any=None):
        if attribute in self.model_extra:
            return self.model_extra[attribute]
        else:
            return default
    
    def update(self, attribute: str, value: Any):
        self.model_extra[attribute] = value
        
    
class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    model: Any = None
    
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

class RouteHelper():
    
    def __init__(self, managers: InternalRequestParameters, responseConfig: ResponseConfiguration, params: Parameters):
        self._managers: InternalRequestParameters = managers
        self._responseConfig: ResponseConfiguration = responseConfig
        self._pagination: PaginationDataModel = None
        self._parameters: Parameters = params
        self._pageSize: int = DEFAULT_PAGE_SIZE
        self._resultSize: int = None
    
    
    def set_page_size(self, pageSize: int):
        self._pageSize = pageSize
        
    
    def _pagination_exists(self, raiseError: bool = True):
        if self._pagination is None:
            if raiseError:
                raise RuntimeError('Attempting to modify or access pagination before initializing')
            else:
                return False
        return True


    def _is_valid_page(self, page: int):
        """ test if the page is valid (w/in range of expected number of pages)"""     

        self._pagination_exists()
    
        if self._pagination.total_num_pages is None:
            raise RuntimeError('Attempting fetch a page before estimating total number of pages')
        
        if page > self._pagination.total_num_pages:
            raise RequestValidationError(f'Request `page` {page} does not exist; this query generates a maximum of {self._pagination.total_num_pages} pages')
        
        return True
    
    
    def page(self):
        if self._parameters is not None:
            return self._parameters.get('page', 1)
        return 1
    
    
    def total_num_pages(self):
        if self._resultSize is None:
            raise RuntimeError('Attempting to page before estimating result size.')
        
        return 1 if self._resultSize < self._pageSize \
            else next((p for p in range(1, MAX_NUM_PAGES) if (p - 1) * self._pageSize > self._resultSize)) - 1
            

    def initialize_pagination(self, raiseError=True):
        """ returns False if not a paged model and raiseError = False """
        if self._responseConfig.model.is_paged():
            self._pagination = PaginationDataModel(
                page=self.page(),
                total_num_pages=self.total_num_pages(),
                paged_num_records=None,
                total_num_records=self._resultSize)
            
            return self._is_valid_page(self._pagination.page)
        else:
            if raiseError:
                raise RuntimeError('Attempt to page a non-pageable response model')
            return False


    def set_paged_num_records(self, numRecords: int):
        self._pagination_exists()
        self._pagination.paged_num_records = numRecords


    def offset(self):
        """ calculate offset for SQL pagination""" 
        self._pagination_exists()
        return None if self._pagination.page == 1 \
            else (self._pagination.page - 1) * self._pageSize


    def cursor(self):
        """ for array pagination; calcs endIndex of previous page as a cursor """
        if self._pagination.page == 1:
            return None
        
        pageRange = self.page_array(self._pagination.page - 1)
        return pageRange.end
    

    def page_array(self, page: int=None) -> Range:
        """ calculates start and end indexes for paging an array """
        self._pagination_exists()
        targetPage = self._pagination.page if page is None else page 
        start = (targetPage - 1) * self._pageSize
        end = start + self._pageSize
        if end > self._resultSize:
            end = self._resultSize
            
        return Range(start=start, end=end)
    
    
    async def generate_response(self, result: Any, isCached=False):
        response = result if isCached else None
        if response is None:
            self._managers.requestData.update_parameters(self._parameters, exclude=INTERNAL_PARAMETERS)

            if self._responseConfig.model.is_paged():
                if not self._pagination_exists(raiseError=False):
                    if self._resultSize is None:
                        self._resultSize = len(result)
                        
                    self.initialize_pagination() 
                    
                self.set_paged_num_records(len(result))
                
                response = self._responseConfig.model(
                    request=self._managers.requestData,
                    pagination=self._pagination,
                    response=result)
            else: 
                response = self._responseConfig.model(
                    request=self._managers.requestData,
                    response=IGVBrowserTrackSelecterResponse.build_table(result) \
                        if self._responseConfig.model == IGVBrowserTrackSelecterResponse \
                            else result
                    )

                
            # cache the response
            await self._managers.internalCache.set(
                self._managers.cacheKey.internal, 
                response, 
                namespace=self._managers.cacheKey.namespace)
            
        match self._responseConfig.format:
            case ResponseFormat.TABLE:
                # cache the response again, this time by the requestId b/c 
                # the cacheKey cannot be passed through the URL  
                cacheKey = self._managers.cacheKey.external   
                requestIsCached = await self._managers.internalCache.exists(cacheKey, namespace=CacheNamespace.VIEW)
                if not requestIsCached:  # then cache it
                    await self._managers.internalCache.set(cacheKey, response, namespace=CacheNamespace.VIEW)
                
                redirectUrl = f'/redirect{RedirectEndpoints.TABLE.value}/{cacheKey}'
                return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
            case ResponseFormat.DOWNLOAD:
                
                return Response(response.to_text(ResponseFormat.DOWNLOAD), media_type='text/plain')
            case _:  
                return response

