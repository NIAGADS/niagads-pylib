from niagads.open_access_api_common.config import core, external_resources


def test_sample():
    assert core is not None


def test_urls():
    assert "FILER" in external_resources.URLS.filer
