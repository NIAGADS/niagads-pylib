import pytest


@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_variants_route(client, content):
    response = client.get(
        "/record/variant/", params={"ids": "rs7412", "content": content}
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert set(records) == {"rs7412"}
    assert records["rs7412"]
    for record in records["rs7412"]:
        assert record["ref_snp_id"] == "rs7412"
        assert record["id"]
        assert record["variant_class"]
        if content == "full":
            assert record["chromosome"]
            assert isinstance(record["position"], int)
            assert record["ref"]
            assert record["alt"]
        else:
            assert "position" not in record


@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_variants_by_positional_id(client, content):
    refsnp_response = client.get("/record/variant/", params={"ids": "rs7412"})
    assert refsnp_response.status_code == 200, refsnp_response.text

    refsnp_records = refsnp_response.json()["data"]["rs7412"]
    assert refsnp_records
    variant_id = refsnp_records[0]["id"]
    response = client.get(
        "/record/variant/",
        params={"ids": f"rs7412,{variant_id}", "content": content},
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert set(records) == {"rs7412", variant_id}
    assert records[variant_id]
    assert all(record["id"] == variant_id for record in records[variant_id])
    for record in records[variant_id]:
        assert ("position" in record) == (content == "full")
    assert records[variant_id] == [
        record for record in records["rs7412"] if record["id"] == variant_id
    ]


@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_variant_route(client, content):
    response = client.get("/record/variant/rs1181874", params={"content": content})

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert records
    for record in records:
        assert record["ref_snp_id"] == "rs1181874"
        assert record["id"]
        assert record["variant_class"]
        if content == "full":
            assert isinstance(record["position"], int)
            assert record["ref"]
            assert record["alt"]
        else:
            assert "position" not in record


@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_variant_associations(client, content):
    response = client.get(
        "/record/variant/rs1181874/associations",
        params={"content": content},
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert records
    if content == "summary":
        assert len({record["track"] for record in records}) == len(records)
    for record in records:
        assert record["track"]
        if content == "full":
            assert record["variant"]
            assert isinstance(record["traits"], dict)
            assert isinstance(record["pvalue"], str)
            assert isinstance(record["neg_log10_pvalue"], (int, float))
        else:
            assert set(record) == {"track", "traits", "num_associations"}
            assert record["traits"] is None or isinstance(record["traits"], dict)
            assert isinstance(record["num_associations"], int)
            assert record["num_associations"] > 0


@pytest.mark.parametrize("flank", [0])
def test_get_variant_associations_summary(client, flank):
    response = client.get(
        "/record/variant/1:3765506:C:A/associations",
        params={"flank": flank, "content": "full"},
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert records
    for record in records:
        assert record["variant"]
        assert isinstance(record["traits"], dict)
        assert isinstance(record["pvalue"], str)
        assert isinstance(record["neg_log10_pvalue"], (int, float))


@pytest.mark.parametrize("flank", [-1, 1000001, "invalid"])
def test_get_variant_associations_invalid_flank(client, flank):
    response = client.get(
        "/record/variant/rs7412/associations", params={"flank": flank}
    )

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["query", "flank"] for error in response.json()["detail"]
    )


def test_get_variants_missing_ids(client):
    response = client.get("/record/variant/")

    assert response.status_code == 422, response.text
    assert any(error["loc"] == ["query", "ids"] for error in response.json()["detail"])
