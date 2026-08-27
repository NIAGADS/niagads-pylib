from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/genes",
    summary="search-gene-records",
    description="Search GenomicsDB gene records using structured keywords and filters.",
)
async def search_genes():
    pass


@router.get(
    "/variants",
    summary="search-variant-records",
    description="Search GenomicsDB variant records using structured keywords and filters.",
)
async def search_variants():
    pass


@router.get(
    "/regions",
    summary="search-region-records",
    description="Search GenomicsDB region records using structured parameters.",
)
async def search_regions():
    pass


@router.get(
    "/tracks",
    summary="search-track-records",
    description="Search GenomicsDB track records using structured keywords and filters.",
)
async def search_tracks():
    pass


@router.get(
    "/tracks/data",
    summary="search-track-data",
    description=(
        "Retrieve GenomicsDB track data, optionally constrained by structured "
        "track metadata filters."
    ),
)
async def search_track_data():
    pass
