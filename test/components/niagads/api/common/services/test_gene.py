import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.services.gene import GeneEndpointService
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.results.associations import VariantAssociation


@pytest.mark.parametrize("track_ids", [[], ["track-a", "track-b", "track-a"]])
def test_fetch_associations_summary(track_ids, monkeypatch):
    associations = [{"track_stable_id": track_id} for track_id in track_ids]
    monkeypatch.setattr(
        VariantAssociation,
        "retrieve_records",
        AsyncMock(return_value={"APOE": associations}),
    )
    monkeypatch.setattr(
        Track,
        "retrieve_records",
        AsyncMock(
            return_value={
                "track-a": [
                    {"participant_phenotypes": {"diagnosis": [], "other": None}}
                ],
                "track-b": [{"participant_phenotypes": None}],
            }
        ),
    )
    service = GeneEndpointService(
        context=SimpleNamespace(database_session=None),
        parameters=None,
        response_config=None,
    )

    records = asyncio.run(service.fetch_associations("APOE", summary=True))

    assert all(isinstance(record, DynamicRecord) for record in records)
    assert [record.model_dump() for record in records] == (
        [
            {
                "track": "track-a",
                "traits": {"diagnosis": []},
                "num_associations": 2,
            },
            {"track": "track-b", "traits": None, "num_associations": 1},
        ]
        if track_ids
        else []
    )
