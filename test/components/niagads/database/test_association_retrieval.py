import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.results.associations import VariantAssociation
from sqlalchemy.dialects import postgresql


@pytest.mark.parametrize(
    "lookup_value",
    [7, "123", OneBasedGenomicRegion(chromosome="chr1", start=10, end=20)],
)
def test_association_queries_join_tracks_and_project_stable_track_id(
    lookup_value, monkeypatch
):
    monkeypatch.setattr(IntervalBin, "find_bin_index", AsyncMock(return_value="chr1"))
    record = {
        "track_stable_id": "stable-track",
        "variant_stable_id": "chr1:10:A:G",
    }
    key = (
        str(lookup_value)
        if isinstance(lookup_value, OneBasedGenomicRegion)
        else lookup_value
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [record]
    session = AsyncMock()
    session.execute.return_value = result

    records = asyncio.run(VariantAssociation.retrieve_records(session, lookup_value))

    assert records == {key: [record]}
    session.execute.assert_awaited_once()
    compiled = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "JOIN dataset.track ON" in sql
    assert "dataset.track.track_id = results.variantassociation.track_id" in sql
    assert "results.variantassociation.track_id AS track_id" in sql
    assert "dataset.track.source_id AS track_stable_id" in sql
    assert "row_to_json(association_matches)" in sql
    assert "AS JSONB) -" in sql
    assert "track_id" in compiled.params.values()
    if isinstance(lookup_value, int):
        assert "variantassociation.track_id =" in sql
    elif isinstance(lookup_value, str):
        assert "variantassociation.variant_stable_id =" in sql
    else:
        assert "variantassociation.chromosome =" in sql
        assert " @> " in sql
        assert " && " in sql


@pytest.mark.parametrize("lookup_value", [7, "123"])
def test_unmatched_association_lookup_retains_empty_mapping(lookup_value):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    assert asyncio.run(VariantAssociation.retrieve_records(session, lookup_value)) == {
        lookup_value: []
    }
