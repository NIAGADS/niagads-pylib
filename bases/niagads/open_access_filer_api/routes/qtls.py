from fastapi import APIRouter, Depends, Query
from typing import Union

from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.features.bed import BEDResponse
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import loc_param
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.path import track_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_filer_api.dependencies import InternalRequestParameters
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper

# TODO: Fix documentation and route nomenclature

router = APIRouter(
    prefix="/qtl",
    tags=BASE_TAGS
    + [
        str(SharedOpenAPITags.TRACK_DATA),
        str(SharedOpenAPITags.XQTL_TRACK_RECORD),
    ],
)

tags = ["Data Retrieval by Region", "xQTL Track Record"]


@router.get(
    "/{track}",
    tags=tags,
    name="Get QTLs by Region[Beta]",
    response_model=Union[BEDResponse, TableViewResponse, GenericResponse],
    description="retrieve xQTL data from FILER for the specified genomic region or sequence feature",
)
async def get_feature_qtl(
    track=Depends(track_param),
    loc: str = Depends(loc_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.full_data(description=True)
    ),
    format: str = Query(
        ResponseFormat.JSON,
        description=ResponseFormat.functional_genomics(description=True),
    ),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends(),
) -> Union[BEDResponse, TableViewResponse, GenericResponse]:

    rContent = ResponseContent.data().validate(content, "content", ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
            view=ResponseView.validate(view, "view", ResponseView),
            model=BEDResponse if rContent == ResponseContent.FULL else GenericResponse,
        ),
        Parameters(track=track, location=loc, page=page),
    )

    return await helper.get_feature_qtls()
