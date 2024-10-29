from fastapi import APIRouter

from api.common.exceptions import RESPONSES

from api.routers.view.common.constants import ROUTE_TAGS

from .table import router as TableRouter

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/view",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/", tags=TAGS, name="about",
            description="About Views")
async def read_root():
    return {"msg": "`/views` endpoints are internal redirects that pass responses to visualizations"}

router.include_router(TableRouter)