from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums.response_properties import ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.features import loc_param
from api.dependencies.parameters.optional import page_param
from api.dependencies.parameters.identifiers import path_track_id
from api.models.base_response_models import BaseResponseModel
from api.models.view_models import TableViewResponse

from api.routes.filer.dependencies.parameters import InternalRequestParameters
from api.routes.filer.common.helpers import FILERRouteHelper
from api.routes.filer.models.bed_features import BEDResponse

router = APIRouter(prefix="/qtl", responses=RESPONSES)

tags = ["Record by ID", "Track Data by ID"]

@router.get("/{track}/", tags=tags,
    name="Get QTLs by Sequence Feature",
    response_model=Union[BEDResponse, TableViewResponse, BaseResponseModel],
    description="retrieve qtl data from FILER for the specific genomic region")

async def get_feature_qtl(
    track = Depends(path_track_id),
    loc:str=Depends(loc_param),
    page:int=Depends(page_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.full_data(description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.functional_genomics(description=True)),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends()
) -> Union[BEDResponse, TableViewResponse, BaseResponseModel]:
    
    rContent = ResponseContent.data().validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=ResponseFormat.functional_genomics().validate(format, 'format', ResponseFormat),
            view=ResponseView.validate(view, 'view', ResponseView),
            model=BEDResponse if rContent == ResponseContent.FULL \
                else BaseResponseModel
        ),
        Parameters(track=track, location=loc, page=page)
    )

    return await helper.get_feature_qtls()
