from fastapi import APIRouter

router = APIRouter(prefix="/record/track", tags=["Records", "Tracks"])


@router.get(
    "/{track}",
    summary="get-track-record",
    description="Retrieve the canonical GenomicsDB track record by track identifier.",
)
async def get_track_record(track: str):
    pass


@router.get(
    "/{track}/data",
    summary="get-track-data",
    description="Retrieve data from a known GenomicsDB track.",
)
async def get_track_data(track: str):
    pass
