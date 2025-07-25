from typing import List, Union
from fastapi import APIRouter, Depends, Query
from niagads.api_common.config import Settings
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.annotations.regions import RegionVariant
from niagads.api_common.models.features.gene import RegionGene
from niagads.api_common.models.features.genomic import (
    GenomicFeature,
    GenomicRegion,
    RegionResponse,
)
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.parameters.record.path import region_param
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import Parameters, ResponseConfiguration
from niagads.api_common.views.table import TableViewResponse
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import APP_NAME
from niagads.genomics_api.queries.records.region import (
    RegionGeneQuery,
    RegionRecordQuery,
    RegionStructuralVariantQuery,
    RegionVariantQuery,
)
from niagads.genomics_api.services.route import GenomicsRouteHelper


router = APIRouter(
    prefix="/record/region",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.ENTITY_LOOKUP),
    ],
)


@router.get(
    "/{region}",
    response_model=RegionResponse,
    name="Get region record",
    description="retrieve an annotated region",
)
async def get_region(
    region: GenomicFeature = Depends(region_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> RegionResponse:

    svs_only: bool = not region.is_within_range_limit(max_span)
    response_content = ResponseContent.FULL
    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            model=(RegionResponse),
        ),
        Parameters(id=region.feature_id, svs_only=svs_only),
        query=RegionRecordQuery,
    )

    return await helper.get_region_record()


max_span = Settings.from_env().MAX_SPAN_SIZE


class RegionAnnotationResponse(RecordResponse):
    data: Union[List[RegionVariant], List[RegionGene]]


@router.get(
    "/{region}/variants",
    response_model=Union[RegionAnnotationResponse, RecordResponse, TableViewResponse],
    name="Get co-located variants",
    description=f"retrieve variants contained within or overlapping this region.  If the regions is > {max_span} bp, only structural variants will be retrieved",
)
async def get_region_variants(
    region: GenomicFeature = Depends(region_param),
    svsOnly: bool = Query(default=False, description="fetch structural variants only"),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[RegionAnnotationResponse, RecordResponse, TableViewResponse]:

    svs_only: bool = svsOnly or not region.is_within_range_limit(max_span)

    response_content = ResponseContent.FULL
    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    response_view = ResponseView.table().validate(view, "view", ResponseView)

    genomic_region = GenomicRegion.from_region_id(region.feature_id)

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            view=response_view,
            model=RegionAnnotationResponse,
        ),
        Parameters(
            id=region.feature_id,
            svs_only=svs_only,
            chromosome=str(genomic_region.chromosome),
            start=genomic_region.start,
            end=genomic_region.end,
        ),
        query=RegionStructuralVariantQuery if svs_only else RegionVariantQuery,
    )

    return await helper.get_query_response()


@router.get(
    "/{region}/genes",
    response_model=Union[RegionAnnotationResponse, RecordResponse, TableViewResponse],
    name="Get co-located genes",
    description=f"retrieve genes contained within or overlapping this region.",
)
async def get_region_genes(
    region: GenomicFeature = Depends(region_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[RegionAnnotationResponse, RecordResponse, TableViewResponse]:

    response_content = ResponseContent.FULL
    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    response_view = ResponseView.table().validate(view, "view", ResponseView)

    genomic_region = GenomicRegion.from_region_id(region.feature_id)

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            view=response_view,
            model=RegionAnnotationResponse,
        ),
        Parameters(
            id=region.feature_id,
            chromosome=str(genomic_region.chromosome),
            start=genomic_region.start,
            end=genomic_region.end,
        ),
        query=RegionGeneQuery,
    )

    return await helper.get_query_response()
