from fastapi import APIRouter

router = APIRouter(prefix="/record/region", tags=["Records", "Regions"])


@router.get(
    "/{region}",
    summary="get-region-record",
    description="Retrieve the canonical GenomicsDB region record by genomic region.",
)
async def get_region_record(region: str):
    pass


@router.get(
    "/{region}/genes",
    summary="get-region-genes",
    description="Retrieve genes located in or overlapping a genomic region.",
)
async def get_region_genes(region: str):
    pass


@router.get(
    "/{region}/variants",
    summary="get-region-variants",
    description="Retrieve variants located in or overlapping a genomic region.",
)
async def get_region_variants(region: str):
    pass
