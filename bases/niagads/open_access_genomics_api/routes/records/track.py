from fastapi import APIRouter, Depends, Path, Query
from typing import Union

from niagads.exceptions.core import ValidationError
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.features.feature_score import (
    GWASSumStatResponse,
    QTLResponse,
)
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    AbridgedTrackResponse,
)
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
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
from niagads.open_access_genomics_api.dependencies import InternalRequestParameters
from niagads.open_access_genomics_api.documentation import APP_NAME
from niagads.open_access_genomics_api.queries.track_data import (
    CountsAbridgedTrackQuery,
    TopAbridgedTrackQuery,
)
from niagads.open_access_genomics_api.queries.track_metadata import TrackMetadataQuery
from niagads.open_access_genomics_api.services.route import GenomicsRouteHelper


router = APIRouter(
    prefix="/record/track",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.TRACK_RECORD),
    ],
)


@router.get(
    "/{track}",
    response_model=Union[AbridgedTrackResponse, TrackResponse, GenericResponse],
    name="Get track metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response",
)
async def get_track_metadata(
    track=Depends(track_param),
    content: str = Query(
        ResponseContent.BRIEF,
        description=ResponseContent.descriptive(description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[AbridgedTrackResponse, TrackResponse, GenericResponse]:

    rContent = ResponseContent.descriptive().validate(
        content, "content", ResponseContent
    )
    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=rFormat,
            model=(
                TrackResponse
                if rContent == ResponseContent.FULL
                else AbridgedTrackResponse
            ),
        ),
        Parameters(track=track),
        # idParameter='track',
        # query=TrackMetadataQuery
    )

    return await helper.get_track_metadata()
    # return await helper.get_query_response()


tags = [str(SharedOpenAPITags.TRACK_DATA)]


@router.get(
    "/{track}/data",
    tags=tags,
    name="Get track data",
    response_model=Union[
        GWASSumStatResponse,
        QTLResponse,
        AbridgedTrackResponse,
        TableViewResponse,
        GenericResponse,
    ],
    description="Get the top scoring (most statistically-significant based on a p-value filter) variant associations or QTLs from a data track.",
)
async def get_track_data(
    track=Depends(track_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.data(description=True)
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.variant_score(description=True)
    ),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends(),
) -> Union[
    GWASSumStatResponse,
    QTLResponse,
    AbridgedTrackResponse,
    TableViewResponse,
    GenericResponse,
]:

    rContent = ResponseContent.data().validate(content, "content", ResponseContent)

    # GWAS, QTL, Table response models will be updated by the helper depending on query result
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=ResponseFormat.variant_score().validate(
                format, "format", ResponseFormat
            ),
            view=ResponseView.validate(view, "view", ResponseView),
            model=(
                AbridgedTrackResponse
                if rContent == ResponseContent.BRIEF
                else GenericResponse
            ),
        ),
        Parameters(track=track, page=page),
        query=TrackMetadataQuery,
        idParameter="track",
    )

    return await helper.get_track_data_query_response()


@router.get(
    "/{track}/data/summary/{summary_type}",
    tags=tags,
    name="Get track data summary",
    response_model=GenericResponse,
    description="Get a summary of the top scoring (most statistically-significant based on a p-value filter) variant associations or QTLs from a data track.",
)
async def get_track_data_summary(
    track=Depends(track_param),
    summary_type=Path(description="summary type: one of counts or top"),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.data(description=True)
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.variant_score(description=True)
    ),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends(),
) -> GenericResponse:

    # TODO: Enum for summary type
    if summary_type not in ["counts", "top"]:
        raise ValidationError("Allowable summary types: `counts` or `top`")

    rContent = ResponseContent.data().validate(content, "content", ResponseContent)

    # GWAS, QTL, Table response models will be updated by the helper depending on query result
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=ResponseFormat.variant_score().validate(
                format, "format", ResponseFormat
            ),
            view=ResponseView.validate(view, "view", ResponseView),
            model=GenericResponse,
        ),
        Parameters(track=track),
        query=(
            CountsAbridgedTrackQuery
            if summary_type == "counts"
            else TopAbridgedTrackQuery
        ),
        idParameter="track",
    )

    result = await helper.get_query_response()
    return result
