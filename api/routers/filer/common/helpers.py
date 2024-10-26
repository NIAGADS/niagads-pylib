from fastapi import status
from fastapi.responses import RedirectResponse

from api.common.helpers import HelperParameters as __BaseHelperParameters
from api.common.formatters import clean, convert_str2list
from api.dependencies.parameters.optional import ResponseType
from api.response_models.base_models import BaseResponseModel, RequestDataModel
from api.response_models.data_models import GenericData

from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters


class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters

async def cache_key(requestData: RequestDataModel, model: BaseResponseModel, suffix: str=None):
    if model.is_paged():
        return requestData.request_id + (f'_{suffix}' if suffix is not None else '')
    else: 
        raise NotImplementedError('Need to use auto-generated cache key based on endpoint and parameters')
    
async def get_track_data(opts: HelperParameters):
    countsOnly = getattr(opts.parameters, 'countsOnly', False)
    if countsOnly and opts.format != ResponseType.JSON:
        raise ValueError(f'Invalid response format selected: `{opts.format.value}`; counts can only be returned in a `JSON` response')
    
    await MetadataQueryService(opts.internal.session).validate_tracks(convert_str2list(opts.parameters.track))
    result = await ApiWrapperService().get_track_hits(clean(opts.parameters.track), opts.parameters.span, countsOnly=countsOnly)

    # in all cases
    # TODO:
    # paged response; by requestId, others by auto-generated based on request and params?
    # cache -> expected response as requestID_response, 
    # cache requestData as requestID_request so that original URL and params are passed   
    rowModel = opts.model.row_model(name=True)
    requestId = opts.internal.requestData.request_id
    match opts.format:
        case ResponseType.TABLE:
            redirectUrl = f'/view/table/{rowModel}?forwardingRequestId={requestId}'
            return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
        case _:
            return opts.model(request=opts.internal.requestData, response=result)


async def get_track_metadata(opts: HelperParameters):
    result = await MetadataQueryService(opts.internal.session).get_track_metadata(convert_str2list(opts.parameters.track))
    # in all cases
    # TODO:
    # cache -> expected response as requestID_response, 
    # cache requestData as requestID_request so that original URL and params are passed
    rowModel = opts.model.row_model(name=True)
    requestId = opts.internal.requestData.request_id
    
    match opts.format:
        case ResponseType.TABLE:
            redirectUrl = f'/view/table/{rowModel}?forwardingRequestId={requestId}'
            return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)

        case _:
            return opts.model(request=opts.internal.requestData, response=result)
        