from fastapi import APIRouter

router = APIRouter(prefix="/service", tags=["Service"])


@router.get(
    "/igvbrowser/feature",
    summary="get-genome-browser-feature",
    description="Retrieve feature location data for the NIAGADS Genome Browser.",
)
async def get_igvbrowser_feature():
    pass


@router.get(
    "/igvbrowser/track/variant",
    summary="get-genome-browser-variant-track",
    description="Retrieve variant track data for the NIAGADS Genome Browser.",
)
async def get_igvbrowser_variant_track():
    pass
