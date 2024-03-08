from fastapi import APIRouter #, Depends

from ...dependencies import RESPONSES
from .dependencies import ROUTE_ABBREVIATION, ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX
from .metadata import router as metadata
from .data import router as data

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
    # dependencies=[Depends(assembly)] -- adds dependencies to every query, but saves in state
)

@router.get("/", tags=ROUTE_TAGS, name="about", description="about the " + ROUTE_NAME)
async def read_root():
    return {"database": "FILER"}

# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------
router.include_router(metadata)
router.include_router(data)