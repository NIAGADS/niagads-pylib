from fastapi import APIRouter

router = APIRouter(prefix="/record/collection", tags=["Records", "Collections"])


@router.get(
    "/",
    summary="get-collections",
    description="List FILER track collections.",
)
async def get_collections():
    pass


@router.get(
    "/{collection}",
    summary="get-collection-record",
    description="Retrieve a FILER collection record and its associated tracks.",
)
async def get_collection_record(collection: str):
    pass
