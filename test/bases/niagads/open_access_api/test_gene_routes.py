def test_get_genes_route(client):
    response = client.get("/record/gene/?ids=APOE,BRCA1")

    assert response.status_code == 200

    records = response.json()["data"]
    assert set(records) == {"APOE", "BRCA1"}

    for identifier, record in records.items():
        assert record["symbol"] == identifier
        assert isinstance(record["nomenclature"], dict)


def test_get_gene_by_ensembl_id(client):
    symbol_response = client.get("/record/gene/?ids=APOE")
    assert symbol_response.status_code == 200

    ensembl_id = symbol_response.json()["data"]["APOE"]["id"]
    response = client.get(f"/record/gene/{ensembl_id}")

    assert response.status_code == 200

    records = response.json()["data"]
    assert len(records) == 1
    assert records[0]["id"] == ensembl_id
    assert isinstance(records[0]["nomenclature"], dict)
