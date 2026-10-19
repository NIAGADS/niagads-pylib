import pytest


def test_get_genes_route(client):
    response = client.get("/record/gene/?ids=APOE,BRCA1")

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert set(records) == {"APOE", "BRCA1"}

    for identifier, records in records.items():
        for rec in records:
            assert rec["gene_symbol"] == identifier
            assert isinstance(rec["xrefs"], dict)


def test_get_genes_route_summary_response(client):
    response = client.get("/record/gene/?ids=APOE,BRCA1&content=summary")

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert set(records) == {"APOE", "BRCA1"}

    for identifier, records in records.items():
        for rec in records:
            assert rec["gene_symbol"] == identifier
            assert rec.get("xrefs") is None


def test_get_gene_by_ensembl_id(client):
    symbol_response = client.get("/record/gene/APOE")
    assert symbol_response.status_code == 200, response.text

    ensembl_id = symbol_response.json()["data"][0]["id"]
    response = client.get(f"/record/gene/{ensembl_id}")

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert len(records) == 1
    assert records[0]["id"] == ensembl_id
    assert isinstance(records[0]["xrefs"], dict)


@pytest.mark.parametrize("flank", [0, 5000])
def test_get_gene_associations(client, flank):
    response = client.get(
        "/record/gene/APOE/associations",
        params={"flank": flank, "content": "full"},
    )

    assert response.status_code == 200, response.text

    records = response.json()["data"]
    assert records
    for record in records:
        assert record["variant"]
        assert record["chromosome"] == "19"
        assert record["track"]
        assert isinstance(record["traits"], dict)
        assert isinstance(record["pvalue"], str)
        assert isinstance(record["neg_log10_pvalue"], (int, float))


# @pytest.mark.parametrize("flank", [0, 5000])
# def test_get_gene_associations_summary(client, flank):
#     response = client.get(
#         "/record/gene/APOE/associations",
#         params={"flank": flank, "content": "summary"},
#     )

#     assert response.status_code == 200, response.text

#     records = response.json()["data"]
#     assert records
#     assert len({record["track"] for record in records}) == len(records)
#     for record in records:
#         assert set(record) == {"track", "traits", "num_associations"}
#         assert record["track"]
#         assert record["traits"] is None or isinstance(record["traits"], dict)
#         assert isinstance(record["num_associations"], int)
#         assert record["num_associations"] > 0


# @pytest.mark.parametrize("flank", [-1, 1000001, "invalid"])
# def test_get_gene_associations_invalid_flank(client, flank):
#     response = client.get("/record/gene/APOE/associations", params={"flank": flank})

#     assert response.status_code == 422, response.text
#     assert any(
#         error["loc"] == ["query", "flank"] for error in response.json()["detail"]
#     )


# @pytest.mark.parametrize("gene_id", ["APOE", "ENSG00000130203"])
# def test_get_gene_structure(client, gene_id):
#     response = client.get(f"/record/gene/{gene_id}/structure")

#     assert response.status_code == 200, response.text

#     records = response.json()["data"]
#     assert len(records) == 1
#     transcripts = records[0]["transcripts"]
#     assert transcripts
#     for transcript in transcripts:
#         assert transcript["id"].startswith("ENST")
#         assert transcript["exons"]
#         for exon in transcript["exons"]:
#             assert exon["id"].startswith("ENSE")
#             assert exon["location"].startswith("chr19:")
