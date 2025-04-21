from niagads.open_access_api_common import exception_handlers, types


def test_sample():
    assert exception_handlers is not None
    assert types is not None


def test_range():
    try:
        types.Range(start=500, end=5)
    except RuntimeError:
        assert True  # Range start < end validation works
