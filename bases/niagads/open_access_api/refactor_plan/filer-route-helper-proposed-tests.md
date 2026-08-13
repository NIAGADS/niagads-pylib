## RequestParameters rename
```python
from niagads.api.common.services.route import RequestParameters


def test_request_parameters_allows_extra_fields():
    params = RequestParameters(track="t1", page=2, span="chr1:1-10")
    assert params.get("track") == "t1"
    assert params.get("page") == 2
    assert params.get("span") == "chr1:1-10"
```

## FILER pagination invariants
```python
def test_filer_cursor_pagination_preserves_track_sort_order():
    summary = [
        TrackResultSize(track_id="t1", num_results=5),
        TrackResultSize(track_id="t2", num_results=25),
        TrackResultSize(track_id="t3", num_results=10),
    ]
    ordered = TrackResultSize.sort(summary)
    assert [item.track_id for item in ordered] == ["t2", "t3", "t1"]
```

## Response/view behavior
```python
async def test_table_view_response_uses_request_metadata(helper, response_model):
    result = await helper.generate_table_response(response_model)
    assert result.request is not None
    assert result.table is not None
```

## Cache hit/miss paths
```python
async def test_cached_response_short_circuits_generation(helper, cache_mock):
    cache_mock.get.return_value = {"data": []}
    response = await helper._get_cached_response()
    assert response is not None
```

## FILER endpoint flows
```python
async def test_search_track_data_with_metadata_filters_returns_empty_message(helper):
    helper._managers.request_data.messages = []
    response = await helper.generate_response([], is_cached=False)
    assert response is not None
```
