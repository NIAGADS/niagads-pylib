from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional

from api.common.helpers import HelperParameters as __BaseHelperParameters
from api.response_models import VizTableResponse, BEDResponse
from api.dependencies.shared_params import ResponseType
from api.dependencies.param_validation import clean, convert_str2list

from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters


class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters


async def get_track_metadata(opts: HelperParameters):
    result = await MetadataQueryService(opts.internal.session).get_track_metadata(convert_str2list(opts.parameters['track']))
    match opts.format:
        case ResponseType.TABLE:
            raise NotImplementedError('Interactive Table View coming soon')
            # ResponseRedirect()
        case _:
            return opts.model(request=opts.internal.requestData, response=result)
        
        
    """ 
    else:
        # FIXME: cache in memory store; revisit when caching is set up
        request.session[requestData.request_id + '_response'] = [t.serialize(promoteObjs=True, collapseUrls=True) for t in result]
        request.session[requestData.request_id + '_request'] = requestData.serialize()
        # redirectUrl = f'/view/table/filer_track?forwardingRequestId={requestData.request_id}'
        # return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
    """