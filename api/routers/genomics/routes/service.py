from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError

from api.common.enums import ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.models.base_response_models import BaseResponseModel
from api.models.genome import GenomicRegion
from api.models.igvbrowser import IGVBrowserTrackConfig, IGVBrowserTrackSelectorResponse, IGVBrowserTrackConfigResponse
from api.models.view_models import TableViewModel


from ..common.helpers import GenomicsRouteHelper
from ..dependencies.parameters import InternalRequestParameters
from ..queries.igvbrowser import FEATURE_LOOKUP

from niagads.reference.chromosomes import Human

router = APIRouter(prefix="/service", responses=RESPONSES)

tags = ["NIAGADS Genome Browser Configuration"]
@router.get("/igvbrowser/feature", tags=tags, response_model=GenomicRegion,
    name="IGV Genome Browser feature lookup service",
    description="retrieve genomic location (variants) or footprint (genes) feature in the format required by the IGV Browser")

async def get_browser_feature_region(
    id: str,
    flank: int = Query(default=0, description='add flanking region +/- `flank` kb up- and downstream to the returned feature location'),
    internal: InternalRequestParameters = Depends()
    ) -> GenomicRegion:

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            view=ResponseView.DEFAULT,
            model=BaseResponseModel
        ),
        Parameters(id=id),
        query=FEATURE_LOOKUP
    )
    
    result = await helper.run_query()
    
    # add the flank
    region = GenomicRegion(**result.response)
    region.start -= flank
    region.end += flank
        
    return region