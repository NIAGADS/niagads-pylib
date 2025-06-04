"""record ID path parameters"""

from typing import Optional
from fastapi import Path, Query
from niagads.exceptions.core import ValidationError
from niagads.utils.string import sanitize


# tracks and collections
async def track_param(track: str = Path(description="data track identifier")) -> str:
    return sanitize(track)


async def collection_param(
    collection: str = Path(description="track collection name"),
) -> str:
    return sanitize(collection)


# genomic features
async def variant_param(variant: str = Query(regex="", description="")):
    return True


async def query_collection_name(
    collection: Optional[str] = Query(default=None, description="track collection name")
) -> str:
    return sanitize(collection)
