import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from niagads.common.models.types import Range
from niagads.database.genomicsdb.intervals import (
    fetch_bin_index_reference,
    find_bin_index,
)
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.genomicsdb_etl.plugins.common.mixins.intervals import (
    BinIndexReferenceMixin,
)


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (10, 20, "chr1.L1.B1"),
        (60, 70, "chr1.L1.B2"),
        (40, 60, "chr1"),
        (10, 50, "chr1"),
        (0, 20, None),
        (90, 101, None),
    ],
)
def test_find_smallest_enclosing_bin(start, end, expected):
    reference = {
        "chr1": {
            1: {
                "starts": [1, 51],
                "bins": [(50, "chr1.L1.B1"), (100, "chr1.L1.B2")],
            },
            0: {"starts": [1], "bins": [(100, "chr1")]},
        }
    }

    assert find_bin_index(reference, "chr1", Range(start=start, end=end)) == expected


def test_loaded_reference_supports_functional_and_etl_lookup():
    rows = [
        IntervalBin(
            chromosome="chr1",
            bin_level=1,
            span=Range(start=1, end=50),
            bin_index="chr1.L1.B1",
        ),
        IntervalBin(
            chromosome="chr1",
            bin_level=0,
            span=Range(start=1, end=100),
            bin_index="chr1",
        ),
    ]
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session = AsyncMock()
    session.execute.return_value = result
    span = Range(start=10, end=20)

    reference = asyncio.run(fetch_bin_index_reference(session))
    assert find_bin_index(reference, "chr1", span) == "chr1.L1.B1"

    loader = BinIndexReferenceMixin()
    asyncio.run(loader._fetch_bin_index_mapping(session))
    assert loader._find_bin_index("chr1", span) == "chr1.L1.B1"
