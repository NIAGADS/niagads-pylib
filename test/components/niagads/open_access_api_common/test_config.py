from niagads.common.constants import external_resources
from niagads.open_access_api_common.config import core


def test_sample():
    assert core is not None


def test_urls():
    assert "FILER" in external_resources.URLS.filer
