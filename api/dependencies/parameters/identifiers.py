from typing import Optional
from fastapi import Path, Query

from api.common.formatters import clean

async def path_variant_id(variant: str = Query(regex="", description="")):
    return True

async def path_track_id(track: str = Path(description="data track identifier")) -> str:
    return clean(track)

async def path_collection_name(collection: str = Path(description="track collection name")) -> str:
    return clean(collection)

async def query_collection_name(collection: Optional[str] = Query(default=None, description="track collection name")) -> str:
    return clean(collection)