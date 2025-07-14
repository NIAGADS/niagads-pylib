from typing import List
from fastapi import APIRouter, Depends
from niagads.api_common.models.datasets.igvbrowser import (
    IGVBrowserTrackConfig,
    IGVBrowserTrackConfigResponse,
    IGVBrowserTrackSelectorResponse,
)
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly
from niagads.api_common.constants import SharedOpenAPITags

from niagads.api_common.parameters.location import (
    assembly_param,
)
from niagads.api_common.parameters.record.query import (
    optional_collection_param,
)
from niagads.api_common.parameters.record.query import (
    optional_track_list_param,
)
from niagads.api_common.parameters.response import ResponseContent

from niagads.api_common.services.metadata.query import MetadataQueryService
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.api_common.views.table import TableViewResponse
from niagads.open_access_filer_api.dependencies import InternalRequestParameters
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(prefix="/service", tags=BASE_TAGS)

tags = [str(SharedOpenAPITags.GENOME_BROWSER)]


@router.get(
    "/igvbrowser/config",
    tags=tags,
    response_model=List[IGVBrowserTrackConfig],
    summary="get-track-genome-browser-configuration-bulk",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) by ID or collection",
)
# , or keyword search")
async def get_track_browser_config_bulk(
    track=Depends(optional_track_list_param),
    assembly: Assembly = Depends(assembly_param),
    collection: str = Depends(optional_collection_param),
    # keyword: str = Depends(keyword_param),
    internal: InternalRequestParameters = Depends(),
) -> List[IGVBrowserTrackConfig]:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL, model=IGVBrowserTrackConfigResponse
        ),
        Parameters(
            track=track, assembly=assembly, collection=collection
        ),  # , keyword=keyword)
    )

    setParamCount = sum(
        x is not None for x in [collection, track]
    )  # [collection, keyword, track])
    if setParamCount == 0 or setParamCount > 1:
        # FIXME: allow combinations
        raise ValidationError(
            "please provide a value for exactly one of `collection`  or `track`"
        )

    if collection is not None:
        result = await helper.get_collection_track_metadata()
    # elif keyword is not None:
    #    result = await helper.search_track_metadata()
    else:
        result = await helper.get_track_metadata()

    return result.data


@router.get(
    "/igvbrowser/selector",
    tags=tags,
    response_model=TableViewResponse,
    summary="get-genome-browser-track-selector-table-definition",
    description="retrieve NIAGADS Genome Browser track selector table for one or more FILER `track`(s) by ID or collection",
)
# , or keyword")
async def get_track_selector(
    track=Depends(optional_track_list_param),
    assembly: Assembly = Depends(assembly_param),
    collection: str = Depends(optional_collection_param),
    # keyword: str = Depends(keyword_param),
    internal: InternalRequestParameters = Depends(),
) -> TableViewResponse:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL, model=IGVBrowserTrackSelectorResponse
        ),
        Parameters(
            track=track, assembly=assembly, collection=collection
        ),  #  keyword=keyword)
    )

    setParamCount = sum(
        x is not None for x in [collection, track]
    )  # [collection, keyword, track])
    if setParamCount == 0 or setParamCount > 1:
        # FIXME: allow combinations
        raise ValidationError(
            "please provide a value for exactly one of `collection` or `track`"
        )

    if collection is not None:
        result = await helper.get_collection_track_metadata()
    # elif keyword is not None:
    #     result = await helper.search_track_metadata()
    else:
        result = await helper.get_track_metadata()

    return result.data
