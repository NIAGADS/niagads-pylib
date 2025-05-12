"""record ID query parameters"""

from typing import Optional

from fastapi import Query
from niagads.exceptions.core import ValidationError
from niagads.utils.string import sanitize


async def track_param(
    track: str = Query(default=None, description="a track identifier")
) -> str:
    sTrack: str = sanitize(track)
    if sTrack is not None and "," in sTrack:
        raise ValidationError(
            "Lists of track identifiers not allowed for this query.  Please provide a single `track` identifier."
        )
    return sTrack


async def optional_track_param(
    track: Optional[str] = Query(default=None, description="a track identifier")
) -> str:
    sTrack: str = sanitize(track)
    if sTrack is not None and "," in sTrack:
        raise ValidationError(
            "Lists of track identifiers not allowed for this query.  Please provide a single `track` identifier."
        )
    return sTrack


async def optional_track_list_param(
    track: Optional[str] = Query(
        default=None,
        description="a comma separated list of one or more track identifiers",
    )
) -> str:

    sTrack: str = sanitize(track)
    if any(delim in sTrack for delim in [":", "|", ";", " "]):
        raise ValidationError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return sTrack


async def track_list_param(
    track: str = Query(
        description="a comma separated list of one or more track identifiers",
    )
) -> str:
    """required track_list parameter"""
    sTrack: str = sanitize(track)
    if any(delim in sTrack for delim in [":", "|", ";", " "]):
        raise ValidationError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return sTrack
