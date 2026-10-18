import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from niagads.open_access_api.app import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def example_gene_record_mapping_response():
    path = Path(__file__).parent / "data" / "gene_record_mapping_response.json"
    return json.loads(path.read_text())
