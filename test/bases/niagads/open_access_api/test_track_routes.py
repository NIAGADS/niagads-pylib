import pytest

TRACK_IDS = (
    "NG00166_04BE648F_STD_OA",
    "NG00165_FB1CA9C2_STD_OA",
)


@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_tracks_route(client, content):
    response = client.get(
        "/record/track/",
        params={"ids": ",".join(TRACK_IDS), "content": content},
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert set(records) == set(TRACK_IDS)
    for track_id in TRACK_IDS:
        assert records[track_id]
        for record in records[track_id]:
            assert record["id"] == track_id
            assert record["name"]
            if content == "full":
                assert isinstance(record["provenance"], dict)
                assert "data_source" in record["provenance"]
            else:
                assert "data_source" in record
                assert "provenance" not in record


@pytest.mark.parametrize("track_id", TRACK_IDS)
@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_track_route(client, track_id, content):
    response = client.get(f"/record/track/{track_id}", params={"content": content})

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert len(records) == 1
    record = records[0]
    assert record["id"] == track_id
    assert record["name"]
    if content == "full":
        assert isinstance(record["provenance"], dict)
        assert "data_source" in record["provenance"]
    else:
        assert "data_source" in record
        assert "provenance" not in record


@pytest.mark.parametrize("track_id", TRACK_IDS)
@pytest.mark.parametrize("content", ["full", "summary"])
def test_get_track_data(client, track_id, content):
    response = client.get(
        f"/record/track/{track_id}/data",
        params={"content": content, "loc": "APOE"},
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert records
    if content == "summary":
        assert len(records) == 1
    for record in records:
        assert record["track"] == track_id
        if content == "full":
            assert record["variant"]
            assert record["chromosome"]
            assert isinstance(record["position"], int)
            assert isinstance(record["traits"], dict)
            assert isinstance(record["pvalue"], str)
            assert isinstance(record["neg_log10_pvalue"], (int, float))
        else:
            assert set(record) == {"track", "traits", "num_associations"}
            assert record["traits"] is None or isinstance(record["traits"], dict)
            assert isinstance(record["num_associations"], int)
            assert record["num_associations"] > 0


def test_get_track_data_requires_location(client):
    response = client.get(f"/record/track/{TRACK_IDS[0]}/data")

    assert response.status_code == 422, response.text
