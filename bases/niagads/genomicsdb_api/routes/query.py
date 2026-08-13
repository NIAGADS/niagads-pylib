from fastapi import APIRouter

router = APIRouter(prefix="/query", tags=["Query"])


@router.get(
    "/genes",
    summary="query-gene-records",
    description="Find GenomicsDB gene records using natural-language or approximate querying.",
)
async def query_genes():
    pass


@router.get(
    "/variants",
    summary="query-variant-records",
    description="Find GenomicsDB variant records using natural-language or approximate querying.",
)
async def query_variants():
    pass


@router.get(
    "/regions",
    summary="query-region-records",
    description="Find GenomicsDB region records using natural-language or approximate querying.",
)
async def query_regions():
    pass


@router.get(
    "/tracks",
    summary="query-track-records",
    description="Find GenomicsDB track records using natural-language or approximate querying.",
)
async def query_tracks():
    pass


@router.get(
    "/tracks/data",
    summary="query-track-data",
    description="Retrieve GenomicsDB track data using natural-language or approximate querying.",
)
async def query_track_data():
    pass
