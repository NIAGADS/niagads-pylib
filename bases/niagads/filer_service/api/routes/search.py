from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/tracks",
    summary="search-track-records",
    description="Search FILER track records using structured keywords and filters.",
)
async def search_tracks():
    pass


@router.get(
    "/tracks/data",
    summary="search-track-data",
    description=(
        "Retrieve FILER track data by region, optionally constrained by structured "
        "track metadata filters."
    ),
)
async def search_track_data():
    pass
