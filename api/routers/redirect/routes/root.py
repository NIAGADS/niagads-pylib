from fastapi import APIRouter

from api.common.exceptions import RESPONSES

from ..common.constants import ROUTE_TAGS

from .view import router as ViewRouter

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/redirect",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/", name="about",
            description="About Redirects")
async def read_root():
    return {"msg": "`/views` endpoints are internal redirects that pass responses to visualizations"}

router.include_router(ViewRouter)