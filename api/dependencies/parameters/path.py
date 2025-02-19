
from fastapi import Path

from api.common.formatters import clean

async def path_track_id(track: str = Path(description="data track identifier")) -> str:
    return clean(track)