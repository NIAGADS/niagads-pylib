from typing import Any
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from api.common.helpers import HelperParameters as __BaseHelperParameters, Parameters
from api.common.formatters import clean, convert_str2list
from api.dependencies.parameters.optional import ResponseType
from api.response_models.base_models import BaseResponseModel, RequestDataModel, PaginationDataModel

from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters


class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters

async def __generate_cache_key(requestData: RequestDataModel, model: BaseResponseModel, suffix: str=None):
    if model.is_paged():
        return requestData.request_id + (f'_{suffix}' if suffix is not None else '')
    else: 
        raise NotImplementedError('Need to use auto-generated cache key based on endpoint and parameters')


# TODO:
# paged response; by requestId, others by auto-generated based on request and params?
# cache -> expected response as requestID_response, 
# cache requestData as requestID_request so that original URL and params are passed   

def __validate_params(format: ResponseType, opts: Parameters ):
    countsOnly = getattr(opts, 'countsOnly', False)
    idsOnly = getattr(opts, 'idsOnly', False )
    if countsOnly and opts.format != ResponseType.JSON:
        raise RequestValidationError(f'Invalid response format selected: `{opts.format.value}`; counts can only be returned in a `JSON` response')
    if idsOnly and countsOnly:
        raise RequestValidationError("please set only one of `idsOnly` or `countsOnly` to `true`")

def __generate_response(result: Any, opts:HelperParameters):
    rowModel = opts.model.row_model(name=True)
    requestId = opts.internal.requestData.request_id
    isPaged = opts.model.is_paged()
    if isPaged:
        numRecords = len(result)
        pagination = PaginationDataModel(page=1, total_num_pages=1, paged_num_records=numRecords, total_num_records=numRecords)

    match opts.format:
        case ResponseType.TABLE:
            redirectUrl = f'/view/table/{rowModel}?forwardingRequestId={requestId}'
            return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
        case _:
            if isPaged:
                return opts.model(request=opts.internal.requestData, pagination=pagination, response=result)
            return opts.model(request=opts.internal.requestData, response=result)


async def get_track_data(opts: HelperParameters):
    __validate_params(opts.format, opts.parameters)
    countsOnly = getattr(opts, 'countsOnly', False)
    
    await MetadataQueryService(opts.internal.session).validate_tracks(convert_str2list(opts.parameters.track))
    result = await ApiWrapperService().get_track_hits(clean(opts.parameters.track), opts.parameters.span, countsOnly=countsOnly)

    return __generate_response(result, opts)


async def get_track_metadata(opts: HelperParameters):
    result = await MetadataQueryService(opts.internal.session).get_track_metadata(convert_str2list(opts.parameters.track))
    return __generate_response(result, opts)


async def search_track_metadata(opts: HelperParameters):
    result =  await MetadataQueryService(opts.internal.session) \
        .query_track_metadata(opts.parameters.assembly, 
            opts.parameters.filter, opts.parameters.keyword, opts.parameters.options)
        
    return __generate_response(result, opts)