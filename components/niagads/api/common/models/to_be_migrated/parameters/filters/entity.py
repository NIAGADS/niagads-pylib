"""record ID path parameters"""

from typing import Optional
from fastapi import Query
from niagads.api.common.models.domain.parameters.utils import parse_comma_separated_list
from niagads.api.common.utils import sanitize
from niagads.exceptions.core import ValidationError


async def collection_filter(
    collection: Optional[str] = Query(
        default=None,
        description="Unique, stable identifier (e.g., NIAGADS acccesion number) or exact name identifying a track collection.",
    )
) -> str:
    return sanitize(collection)


async def track_filter(
    track: Optional[str] = Query(
        default=None,
        description="Comma separated list of one or more Track (data file) identifier (FILER Accession or DSS File ID)",
    )
) -> list[str]:
    return parse_comma_separated_list(sanitize(track))
