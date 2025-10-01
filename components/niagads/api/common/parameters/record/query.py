"""record ID query parameters"""

from typing import Optional

from fastapi import Query
from niagads.api.common.parameters.igvbrowser import ADSPRelease, AnnotatedVariantTrack
from niagads.exceptions.core import ValidationError
from niagads.utils.string import sanitize


async def track_param(
    track: str = Query(default=None, description="a track identifier")
) -> str:
    clean_track: str = sanitize(track)
    if clean_track is not None and "," in clean_track:
        raise ValidationError(
            "Lists of track identifiers not allowed for this query.  Please provide a single `track` identifier."
        )
    return clean_track


async def optional_track_param(
    track: Optional[str] = Query(default=None, description="a track identifier")
) -> str:
    clean_track: str = sanitize(track)
    if clean_track is not None and "," in clean_track:
        raise ValidationError(
            "Lists of track identifiers not allowed for this query.  Please provide a single `track` identifier."
        )
    return clean_track


async def optional_track_list_param(
    track: Optional[str] = Query(
        default=None,
        description="a comma separated list of one or more track identifiers",
    )
) -> str:

    clean_track: str = sanitize(track)
    if any(delim in clean_track for delim in [":", "|", ";", " "]):
        raise ValidationError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return clean_track


async def track_list_param(
    track: str = Query(
        description="a comma separated list of one or more track identifiers",
    )
) -> str:
    """required track_list parameter"""
    clean_track: str = sanitize(track)
    if any(delim in clean_track for delim in [":", "|", ";", " "]):
        raise ValidationError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return clean_track


async def optional_collection_param(
    collection: Optional[str] = Query(default=None, description="track collection name")
) -> str:
    return sanitize(collection)


async def adsp_release_param(
    release: str = Query(
        default=None, description=f"ADSP release.  {ADSPRelease.get_description()}"
    ),
):
    return ADSPRelease(release)


async def variant_track_param(
    track: str = Query(
        description=f"Key for the annotated variant track.  {AnnotatedVariantTrack.get_description()}"
    ),
):
    return AnnotatedVariantTrack(track)
