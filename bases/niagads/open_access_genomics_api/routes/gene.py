from fastapi import APIRouter
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_genomics_api.documentation import APP_NAME

router = APIRouter(
    prefix="/track",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.GENE_RECORD),
    ],
)


@router.get(
    "/{gene}",
    response_model=Union[AbridgedTrackResponse, TrackResponse, GenericResponse],
    name="Get gene record",
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
