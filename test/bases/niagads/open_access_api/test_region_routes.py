import pytest


@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_region_associations(client, content):
    response = client.get(
        "/record/region/associations",
        params={"region": "chr1:3765506-3765506", "content": content},
    )

    assert response.status_code == 200, response.text
    records = response.json()["data"]
    assert records
    for record in records:
        assert record["track"]
        assert isinstance(record["traits"], dict)
        if content == "full":
            assert record["variant"]
            assert record["position"] == 3765506
            assert isinstance(record["pvalue"], str)
        else:
            assert record["num_associations"] > 0


@pytest.mark.parametrize(
    "parameters",
    [
        {"region": "chr1:100-200"},
        {"chr": "chr1", "start": 100, "end": 200},
    ],
)
def test_get_region_variants_pending_integration(client, parameters):
    response = client.get("/record/region/variants", params=parameters)

    assert response.status_code == 501, response.text


@pytest.mark.parametrize("annotation", ["associations", "variants"])
@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"region": "invalid"},
        {"chr": "chr1", "start": 200, "end": 100},
        {"region": "chr1:100-200", "start": 100},
    ],
)
def test_get_region_invalid_coordinates(client, annotation, parameters):
    response = client.get(f"/record/region/{annotation}", params=parameters)

    assert response.status_code == 422, response.text
