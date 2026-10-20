# Open Access API developer notes

For new routes and ASK operation registration, see
[Writing Open Access API endpoints](ENDPOINT_DEVELOPMENT.md).

## Interval-bin reference

Application startup loads the GenomicsDB interval-bin reference into
`app.state.bin_index_reference` using the configured database session manager.
The startup session closes before the application accepts requests. A loading
failure prevents startup. Each application worker loads its own copy.

Endpoints that need a bin index can opt in through `get_bin_index_reference`.
The dependency returns the shared mapping without copying it or querying the
database. Treat the mapping as read-only. It is not part of
`OpenAccessEndpointContext`.

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.intervals import find_bin_index
from niagads.open_access_api.dependencies import get_bin_index_reference

router = APIRouter()


@router.get("/region/bin")
async def get_region_bin(
    region: str,
    bin_index_reference: Annotated[dict, Depends(get_bin_index_reference)],
) -> str | None:
    """Find the enclosing bin for a genomic region.

    Args:
        region (str): Genomic region identifier, such as chr1:100-200.
        bin_index_reference (dict): Shared interval-bin reference.

    Returns:
        str | None: Enclosing bin index, or None if no bin contains the region.
    """
    span = OneBasedGenomicRegion.from_region_id(region)
    bin_index = find_bin_index(bin_index_reference, str(span.chromosome), span.range)
    return str(bin_index) if bin_index is not None else None
```

This is a usage example, not a registered application route. Services can use
the same function with the mapping passed by their endpoint.

The lookup retains the ETL boundary convention: the region end must be strictly
less than the bin end. The bin index narrows candidate records; region queries
still need chromosome and range-overlap conditions.
