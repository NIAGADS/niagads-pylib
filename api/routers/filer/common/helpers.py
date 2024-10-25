from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional

from api.common.helpers import HelperParameters as __BaseHelperParameters
from api.response_models import VizTableResponse, BEDResponse
from api.dependencies.shared_params import ResponseType
from api.dependencies.param_validation import clean, convert_str2list

from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters

def response_type(rType: ResponseType, default: Any):
    match rType:
        case ResponseType.TABLE:
            return VizTableResponse
        # case ResponseType.JSON:
        #     return default
        case _:
            return default

class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters


async def get_track_metadata(opts: HelperParameters):
    result = await MetadataQueryService(opts.internal.session).get_track_metadata(convert_str2list(opts.parameters['track']))
    model = response_type(ResponseType(opts.format), opts.responseModel)
    return model(request=opts.internal.requestData, response=result)