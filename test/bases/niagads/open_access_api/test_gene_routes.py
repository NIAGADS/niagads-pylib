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
