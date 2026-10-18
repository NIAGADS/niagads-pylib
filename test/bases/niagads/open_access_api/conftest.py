import pytest
from fastapi.testclient import TestClient

from niagads.open_access_api.app import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
