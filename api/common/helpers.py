from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi import status
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Any, Dict

from api.common.enums import ResponseContent
from api.dependencies.parameters.services import InternalRequestParameters
from api.dependencies.parameters.optional import PaginationParameters, ResponseFormat
from api.response_models.base_models import BaseResponseModel, PaginationDataModel

# basically allow creation of an arbitrary namespace
class Parameters(BaseModel):
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
class HelperParameters(BaseModel, arbitrary_types_allowed=True):
    internal: InternalRequestParameters
    model: Any
    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    pagination: PaginationParameters = None
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
        

def generate_response(result: Any, opts:HelperParameters):
    rowModel = opts.model.row_model(name=True)
    requestId = opts.internal.requestData.request_id
    isPaged = opts.model.is_paged()
    if isPaged:
        numRecords = len(result)
        page = 1 if opts.pagination is None else opts.pagination.page
        nPages = getattr(opts.parameters, 'total_page_count', 1)
        resultSize = getattr(opts.parameters, 'expected_result_size', numRecords)
        pagination = PaginationDataModel(
            page=page, 
            total_num_pages= nPages, 
            paged_num_records=numRecords, 
            total_num_records=resultSize
        )

    match opts.format:
        case ResponseFormat.TABLE:
            redirectUrl = f'/view/table/{rowModel}?forwardingRequestId={requestId}'
            return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
        case _:
            if isPaged:
                return opts.model(request=opts.internal.requestData, pagination=pagination, response=result)
            return opts.model(request=opts.internal.requestData, response=result)
        

