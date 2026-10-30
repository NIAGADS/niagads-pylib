import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from niagads.api.common.services.track import TrackEndpointService
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.results.associations import VariantAssociation


@pytest.mark.parametrize("summary", [False, True])
@pytest.mark.parametrize("matching", [False, True])
def test_fetch_associations_filters_regional_results(monkeypatch, summary, matching):
    region = OneBasedGenomicRegion(chromosome="chr19", start=100, end=200)
    associations = [
        {"track_stable_id": "other", "variant_stable_id": "chr19:110:A:G"},
        {"track_stable_id": "requested", "variant_stable_id": "chr19:120:T:C"},
        {"track_stable_id": "other", "variant_stable_id": "chr19:130:C:T"},
        {"track_stable_id": "requested", "variant_stable_id": "chr19:140:G:A"},
    ]
    lookup = AsyncMock(return_value={str(region): associations if matching else []})
    monkeypatch.setattr(VariantAssociation, "retrieve_records", lookup)
    service = TrackEndpointService(
        context=SimpleNamespace(database_session=object()),
        parameters=None,
        response_config=None,
    )
    service._lookup_records = AsyncMock()
    service._generate_association_lookup_result = Mock(return_value=[])

    asyncio.run(service.fetch_associations("requested", region=region, summary=summary))

    lookup.assert_awaited_once_with(service._context.database_session, region)
    service._lookup_records.assert_not_awaited()
    service._generate_association_lookup_result.assert_called_once_with(
        [associations[1], associations[3]] if matching else [], summary=summary
    )
