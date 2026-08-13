from fastapi import APIRouter

router = APIRouter(prefix="/query", tags=["Query"])


@router.get(
    "/tracks",
    summary="query-track-records",
    description="Find FILER track records using natural-language or approximate querying.",
)
async def query_tracks():
    pass


@router.get(
    "/tracks/data",
    summary="query-track-data",
    description="Retrieve FILER track data using natural-language or approximate querying.",
)
async def query_track_data():
    pass
