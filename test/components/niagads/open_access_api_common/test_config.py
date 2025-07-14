from niagads.common.constants import external_resources
from niagads.open_access import config


def test_sample():
    assert config is not None


def test_urls():
    assert "FILER" in external_resources.URLS.filer
