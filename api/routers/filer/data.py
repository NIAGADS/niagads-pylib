"""
@api.route('/<string:id>/overlaps', doc={"description": "get track data in the specified span"})
@api.expect(SPAN_PARSER)
class TrackOverlaps(Resource):
    @api.doc(params={'id': 'unique track identifier'})  
    def get(self, id,):
        args = SPAN_PARSER.parse_args()
        validate_track(id, args['assembly'], False)         # if not valid, returns an error
        try:
            span = validate_span(args)
            if isinstance(span, dict):
                return span # error message
            return make_request("get_overlaps", {"id": id, "assembly": args['assembly'], "span": span})
        except ValidationError as err:
            return error_message(str(err), errorType="validation_error")
"""

from fastapi import APIRouter, Depends, Query
from typing import Union, Annotated, Optional

from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param, chromosome_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS, CacheQueryService, ApiWrapperService, TRACK_SEARCH_FILTER_FIELD_MAP

TAGS = ROUTE_TAGS +  ["Data Retrieval"]

router = APIRouter(
    prefix="/overlaps",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/", tags=ROUTE_TAGS, 
    name="Lookup functional genomics track metadata from FILER",
    description="retrieve metadata for (one or more) track(s) by identifier")
async def get_track_data(cacheService: Annotated[CacheQueryService, Depends(CacheQueryService)], 
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
    track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")]):
    # validTracks = cacheService.validate_track_ids(clean(track))
    # return apiWrapperService.get_overlaps(track) # FIXME: .clean()
    return track