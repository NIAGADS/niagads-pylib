from fastapi import APIRouter

router = APIRouter(prefix="/service", tags=["Service"])


@router.get(
    "/igvbrowser/config",
    summary="get-genome-browser-track-config",
    description="Retrieve NIAGADS Genome Browser track configuration for FILER tracks.",
)
async def get_igvbrowser_config():
    pass


@router.get(
    "/igvbrowser/selector",
    summary="get-genome-browser-track-selector",
    description="Retrieve NIAGADS Genome Browser track selector data for FILER tracks.",
)
async def get_igvbrowser_selector():
    pass
