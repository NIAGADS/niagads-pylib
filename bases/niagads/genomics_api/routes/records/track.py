from fastapi import APIRouter, Depends, Path, Query
from typing import Union

from niagads.exceptions.core import ValidationError
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.features.feature_score import (
    GWASSumStatResponse,
    QTLResponse,
)
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.models.datasets.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.api_common.views.table import TableViewResponse
from niagads.api_common.parameters.pagination import page_param
from niagads.api_common.parameters.record.path import track_param
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import APP_NAME
from niagads.genomics_api.queries.track_data import (
    CountsAbridgedTrackQuery,
    TopAbridgedTrackQuery,
)
from niagads.genomics_api.queries.track_metadata import TrackMetadataQuery
from niagads.genomics_api.services.route import GenomicsRouteHelper


router = APIRouter(
    prefix="/record/track",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.ENTITY_LOOKUP),
    ],
)


@router.get(
    "/{track}",
    response_model=Union[AbridgedTrackResponse, TrackResponse, RecordResponse],
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
) -> Union[AbridgedTrackResponse, TrackResponse, RecordResponse]:

    response_content = ResponseContent.descriptive().validate(
        content, "content", ResponseContent
    )
    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            model=(
                TrackResponse
                if response_content == ResponseContent.FULL
                else AbridgedTrackResponse
            ),
        ),
        Parameters(track=track),
        # idParameter='track',
        # query=TrackMetadataQuery
    )

    return await helper.get_track_metadata()
    # return await helper.get_query_response()


tags = [str(SharedOpenAPITags.DATA)]


@router.get(
    "/{track}/data",
    tags=tags,
    name="Get track data",
    response_model=Union[
        GWASSumStatResponse,
        QTLResponse,
        AbridgedTrackResponse,
        TableViewResponse,
        RecordResponse,
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
    RecordResponse,
]:

    response_content = ResponseContent.data().validate(
        content, "content", ResponseContent
    )

    # GWAS, QTL, Table response models will be updated by the helper depending on query result
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=ResponseFormat.variant_score().validate(
                format, "format", ResponseFormat
            ),
            view=ResponseView.validate(view, "view", ResponseView),
            model=(
                AbridgedTrackResponse
                if response_content == ResponseContent.BRIEF
                else RecordResponse
            ),
        ),
        Parameters(track=track, page=page),
        query=TrackMetadataQuery,
        id_parameter="track",
    )

    return await helper.get_track_data_query_response()


@router.get(
    "/{track}/data/summary/{summary_type}",
    tags=tags,
    name="Get track data summary",
    response_model=RecordResponse,
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
) -> RecordResponse:

    # TODO: Enum for summary type
    if summary_type not in ["counts", "top"]:
        raise ValidationError("Allowable summary types: `counts` or `top`")

    response_content = ResponseContent.data().validate(
        content, "content", ResponseContent
    )

    # GWAS, QTL, Table response models will be updated by the helper depending on query result
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=ResponseFormat.variant_score().validate(
                format, "format", ResponseFormat
            ),
            view=ResponseView.validate(view, "view", ResponseView),
            model=RecordResponse,
        ),
        Parameters(track=track),
        query=(
            CountsAbridgedTrackQuery
            if summary_type == "counts"
            else TopAbridgedTrackQuery
        ),
        id_parameter="track",
    )

    result = await helper.get_query_response()
    return result
