from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.open_access_api.dependencies import OpenAccessEndpointContext
from niagads.open_access_api.routes import service


@pytest.mark.parametrize(
    "identifier,service_class",
    [
        ("APOE", service.GeneEndpointService),
        ("ENSG00000130203", service.GeneEndpointService),
        ("rs429358", service.VariantEndpointService),
        ("chr19:44908684:T:C", service.VariantEndpointService),
        ("DUP_CHR1_4AE4CDB8", service.VariantEndpointService),
    ],
)
def test_feature_service_json(identifier, service_class, monkeypatch):
    location = AsyncMock(
        return_value=OneBasedGenomicRegion(chromosome="chr19", start=100, end=200)
    )
    monkeypatch.setattr(service_class, "get_feature_location", location)
    app = FastAPI()
    app.include_router(service.router)
    app.dependency_overrides[OpenAccessEndpointContext] = lambda: None

    with TestClient(app) as client:
        response = client.get(
            "/service/feature", params={"id": identifier, "flank": 25}
        )

    assert response.status_code == 200
    assert response.json() == {"chr": "chr19", "start": 100, "end": 200}
    location.assert_awaited_once_with(identifier, flank=25)
