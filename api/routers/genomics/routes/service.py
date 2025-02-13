from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.models.igvbrowser import IGVBrowserTrackConfig, IGVBrowserTrackSelectorResponse, IGVBrowserTrackConfigResponse
from api.models.view_models import TableViewModel

from ..dependencies.parameters import InternalRequestParameters
from ..models.service import IGVFeatureRegion
router = APIRouter(prefix="/service", responses=RESPONSES)

tags = ["NIAGADS Genome Browser Configuration"]
@router.get("/igvbrowser/feature", tags=tags, response_model=IGVFeatureRegion,
    name="IGV Genome Browser feature lookup service",
    description="retrieve genomic region associated w/a feature in the format required by the IGV Browser")

async def get_browser_feature_region(
    id: str,
    flank: int = Query(default=1000, description='add flanking region +/- `flank` kb up- and downstream to the returned feature location'),
    internal: InternalRequestParameters = Depends()
    ) -> IGVFeatureRegion:
    pass