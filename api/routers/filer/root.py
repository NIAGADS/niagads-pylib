from fastapi import APIRouter
from .metadata import router as metadata

fullResourceName = "FILER Functional Genomics Repository"
resourceAbbrev = "FILER"

tags = [resourceAbbrev]

router = APIRouter(
    prefix="/filer",
    tags=tags,
    responses={404: {"description": "Not found"}},
)

@router.get("/", tags=['FILER'], name="about", description="about the " + fullResourceName)
async def read_root():
    return {"database": "FILER"}

@router.get("/query/", tags=tags)
async def query(track_id: str, description="query data from FILER"):
    return {"track": track_id, "metadata": "TODO"}


router.include_router(metadata)