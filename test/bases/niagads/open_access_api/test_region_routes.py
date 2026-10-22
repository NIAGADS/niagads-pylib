import pytest


@pytest.mark.parametrize("content", ["full", "summary"])
@pytest.mark.parametrize("chromosome", ["1", "chr1"])
def test_get_region_associations(client, content, chromosome):
    response = client.get(
        f"/record/region/{chromosome}:3765506-3765506/associations",
        params={"content": content},
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


@pytest.mark.parametrize("content", ["full", "summary"])
@pytest.mark.parametrize("chromosome", ["1", "chr1"])
def test_get_region_variants(client, content, chromosome):
    response = client.get(
        f"/record/region/{chromosome}:3765506-3765506/variants",
        params={"content": content},
    )

    assert response.status_code == 200, response.text
    records = response.json()["data"]
    assert records
    for record in records:
        assert record["id"]
        assert record["variant_class"]
        if content == "full":
            assert record["position"] == 3765506
        else:
            assert "position" not in record


@pytest.mark.parametrize("annotation", ["associations", "variants"])
@pytest.mark.parametrize(
    "region",
    [
        "invalid",
        "chr1:200-100",
        "chr1:100-end",
    ],
)
def test_get_region_invalid_coordinates(client, annotation, region):
    response = client.get(f"/record/region/{region}/{annotation}")

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("annotation", ["associations", "variants"])
def test_get_region_requires_path_identifier(client, annotation):
    response = client.get(
        f"/record/region/{annotation}",
        params={"region": "chr1:100-200"},
    )

    assert response.status_code == 404, response.text
