from traceback import print_list
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi import Response, status
from pydantic import BaseModel, field_validator, ConfigDict, model_validator
from typing import Any, Dict, Optional, Union

from api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from api.common.enums import CacheKeyQualifier, ResponseContent, CacheNamespace, ResponseView, ResponseFormat
from api.common.types import Range

from api.dependencies.parameters.services import InternalRequestParameters
from api.models.base_models import CacheKeyDataModel, PaginationDataModel
from api.models.base_response_models import BaseResponseModel, T_ResponseModel
from api.models.igvbrowser import IGVBrowserTrackSelectorResponse
from api.models.view_models import TableViewResponseModel

INTERNAL_PARAMETERS = ['span', '_tracks']
ALLOWABLE_VIEW_RESPONSE_CONTENTS = [ResponseContent.FULL, ResponseContent.SUMMARY]

class PaginationCursor(BaseModel):
    """ pagination cursor """
    key: Union[str, int]
    offset: Optional[int]

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
    view: ResponseView = ResponseView.DEFAULT
    model: T_ResponseModel  = None
    
    # make changes or do validation after instantiation
    # https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_post_init
    def model_post_init(self, __context):
        # adjust the format, content, or view depending on specific combinations
        if self.view != ResponseView.DEFAULT: # all visualizations require JSON responses
            self.format = ResponseFormat.JSON
        

    @model_validator(mode='after')
    def validate_model(self):
        if self.content not in ALLOWABLE_VIEW_RESPONSE_CONTENTS and self.view != ResponseView.DEFAULT:
            raise RequestValidationError(f'Can only generate a `{str(self.view)}` `view` of query result for `{print_list(ALLOWABLE_VIEW_RESPONSE_CONTENTS)}` response content (see `content`)')
    
        if self.content != ResponseContent.FULL and self.format in [ResponseFormat.VCF, ResponseFormat.BED]:
            raise RequestValidationError(f'Can only generate a `{str(ResponseContent.format)}` response for a `FULL` data query (see `content`)')
    
    # from https://stackoverflow.com/a/67366461
    # allows ensurance that model is always a child of BaseResponseModel
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
        
    @field_validator("format")
    def validate_foramt(cls, format):
        try:
            return ResponseFormat(format)
        except NameError:
            raise RequestValidationError(f'Invalid value provided for `format`: {format}')
    
    @field_validator("view")
    def validate_view(cls, view):
        try:
            return ResponseView(view)
        except NameError:
            raise RequestValidationError(f'Invalid value provided for `view`: {format}')


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


    def slice_result_by_page(self, page: int=None) -> Range:
        """ calculates start and end indexes for paging an array """
        self._pagination_exists()
        targetPage = self._pagination.page if page is None else page 
        start = (targetPage - 1) * self._pageSize
        end = start + self._pageSize # don't subtract 1 b/c python slices are not end-range inclusive
        if end > self._resultSize:
            end = self._resultSize
            
        return Range(start=start, end=end)
    
    
    async def generate_table_response(self, response: T_ResponseModel):
        # create an encrypted cache key
        cacheKey = CacheKeyDataModel.encrypt_key(
            self._managers.cacheKey + str(CacheKeyQualifier.VIEW) + ResponseView.TABLE.value)
        
        viewResponse = await self._managers.cache.exists(cacheKey, namespace=CacheNamespace.VIEW)
        
        if viewResponse:
            return viewResponse
        
        requestData = self._managers.requestData
        requestData['request_id'] = cacheKey
        
        viewResponseObj = {'response': response.to_view(ResponseView.TABLE, id=cacheKey),
            'request': requestData}
        
        if self._pagination_exists(raiseError=False):
            viewResponseObj['pagination'] = self._pagination
        
        viewResponse = TableViewResponseModel(**viewResponseObj)

        await self._managers.cache.set(cacheKey, viewResponse, namespace=CacheNamespace.VIEW)
        
        return viewResponse
    
    async def generate_response(self, result: Any, isCached=False):
        response: T_ResponseModel = result if isCached else None
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
                if (self._responseConfig.model == IGVBrowserTrackSelectorResponse):
                    tableId = self._parameters.get('collection', self._managers.cacheKey.encrypt())
                    response = self._responseConfig.model(
                        request=self._managers.requestData,
                        response=IGVBrowserTrackSelectorResponse.build_table(result, tableId))
                else:
                    response = self._responseConfig.model(
                        request=self._managers.requestData,
                        response=result
                    )

            # cache the response
            await self._managers.cache.set(
                self._managers.cacheKey.encrypt(), 
                response, 
                namespace=self._managers.cacheKey.namespace)
            
        match self._responseConfig.view:
            case ResponseView.TABLE | ResponseView.IGV_BROWSER:
                return self.generate_table_response(response)
                        
            case ResponseView.DEFAULT:
                if self._responseConfig.format in [ResponseFormat.TEXT, ResponseFormat.BED, ResponseFormat.VCF]:
                    return Response(response.to_text(self._responseConfig.format), media_type="text/plain")
                else: # JSON
                    return response

            case _:  # JSON
                raise NotImplementedError(f'Cannot generate a response for view of type {str(self._responseConfig.view)}')

            

    
