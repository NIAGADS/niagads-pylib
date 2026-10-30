import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.common.search.types import MatchType
from niagads.common.types import Entity
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.database.genomicsdb.schema.variant.documents import Variant
from sqlalchemy.dialects import postgresql

SEARCH_MODELS = [
    (Track, "dataset", "track", "track_id", Entity.TRACK),
    (Gene, "gene", "document_mv", "gene_id", Entity.GENE),
    (
        OntologyTerm,
        "reference",
        "ontologyterm",
        "ontology_term_id",
        Entity.ONTOLOGY_TERM,
    ),
]


@pytest.mark.parametrize("model,schema,table,primary_key,entity", SEARCH_MODELS)
def test_embedding_search_resolves_catalog_and_limits_ranked_records(
    model, schema, table, primary_key, entity
):
    catalog_result = MagicMock()
    catalog_result.mappings.return_value.first.return_value = {
        "table_name": table,
        "table_id": 42,
        "table_primary_key": primary_key,
        "schema_name": schema,
        "schema_id": 3,
    }
    search_result = MagicMock()
    search_result.mappings.return_value.all.return_value = [
        {
            "matched_record_id": "track-a",
            "matched_record_type": str(entity),
            "matched_record_details": {"label": "Track A", "description": None},
            "matched_text": "Expression observed in the hippocampus and cortex.",
            "match_type": "SEMANTIC",
            "rank": 6,
            "score": 0.9,
        }
    ]
    session = AsyncMock()
    session.execute.side_effect = [catalog_result, search_result]

    matches = asyncio.run(
        model.semantic_search_by_embedding(
            session, "hippocampus", [0.1, 0.2, 0.3], limit=5
        )
    )

    assert session.execute.await_count == 2
    catalog_stmt, search_stmt = (
        call.args[0] for call in session.execute.call_args_list
    )
    catalog_params = catalog_stmt.compile().params.values()
    assert schema in catalog_params
    assert table in catalog_params
    compiled = search_stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "ragdoc.chunkembedding" in sql
    assert "ragdoc.chunkmetadata" in sql
    assert "chunkmetadata.table_id =" in sql
    assert 42 in compiled.params.values()
    assert f".row_id = {schema}.{table}.{primary_key}" in sql
    assert "<=>" in sql
    if model in (Gene, Track):
        assert "DISTINCT ON (ragdoc.chunkmetadata.row_id)" in sql
        assert "chunkmetadata.chunk_text AS matched_text" in sql
        assert "semantic_matches.matched_text" in sql
        assert "GROUP BY" not in sql
        assert "hippocampus" not in compiled.params.values()
        assert "ORDER BY ragdoc.chunkmetadata.row_id," in sql
        assert "DESC, ragdoc.chunkmetadata.chunk_metadata_id ASC" in sql
    else:
        assert "max(" in sql
        assert "GROUP BY" in sql
    assert "document_section =" not in sql
    assert "document_type =" not in sql
    assert sql.count("LIMIT") == 1
    assert search_stmt._limit_clause.value == 5
    assert matches[0].matched_record_id == "track-a"
    assert matches[0].matched_record_type is entity
    assert matches[0].match_type is MatchType.SEMANTIC
    assert matches[0].score == 0.9
    assert matches[0].matched_text == (
        "Expression observed in the hippocampus and cortex."
    )


@pytest.mark.parametrize("model,schema,table,primary_key,entity", SEARCH_MODELS)
def test_embedding_search_propagates_missing_catalog_entry(
    model, schema, table, primary_key, entity
):
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = None
    session.execute.return_value = result

    with pytest.raises(ValueError, match="not found in DB catalog"):
        asyncio.run(model.semantic_search_by_embedding(session, "query", [0.1]))

    session.execute.assert_awaited_once()


@pytest.mark.parametrize("model,schema,table,primary_key,entity", SEARCH_MODELS)
def test_embedding_search_returns_no_matches(model, schema, table, primary_key, entity):
    session = AsyncMock()
    catalog_result = MagicMock()
    catalog_result.mappings.return_value.first.return_value = {
        "table_name": table,
        "table_id": 42,
        "table_primary_key": primary_key,
        "schema_name": schema,
        "schema_id": 3,
    }
    search_result = MagicMock()
    search_result.mappings.return_value.all.return_value = []
    session.execute.side_effect = [catalog_result, search_result]

    assert (
        asyncio.run(model.semantic_search_by_embedding(session, "query", [0.1])) == []
    )


def test_variant_embedding_search_returns_embedded_annotation_text(monkeypatch):
    monkeypatch.setattr(IntervalBin, "find_bin_index", AsyncMock(return_value="1"))
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    session.execute.return_value = result
    span = OneBasedGenomicRegion(chromosome="chr1", start=100, end=200)

    asyncio.run(
        Variant.semantic_search_by_embedding(
            session, "blood", [0.1, 0.2, 0.3], span=span, limit=5
        )
    )

    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    matched_text = statement.selected_columns.matched_text
    assert "functional_annotation_summary" in str(matched_text)
    assert "embedded_text" in compiled.params.values()
    assert "blood" not in compiled.params.values()
    assert "variant.variant.embedding IS NOT NULL" in str(compiled)
    assert statement._limit_clause.value == 5
