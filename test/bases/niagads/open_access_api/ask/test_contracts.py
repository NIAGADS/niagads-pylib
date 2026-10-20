"""Validate authoritative results independently of database/provider access."""

import pytest
from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.open_access_api.ask.contracts import Evidence, Presentation, ResultSet
from niagads.open_access_api.ask.results import ResultStore
from pydantic import ValidationError


def test_provenance_preserves_curated_and_proximity_sources():
    evidence = [
        Evidence(evidence_type="curated", data_source="ADSP GVC TopGenes"),
        Evidence(evidence_type="proximity", data_source="track-1", variant="rs1"),
    ]
    result = ResultSet(kind="genes", rows=[{"id": "gene-1", "evidence": evidence}])
    assert [e.data_source for e in evidence] == ["ADSP GVC TopGenes", "track-1"]
    assert result.model_dump(mode="json")["rows"][0]["evidence"][1]["variant"] == "rs1"


def test_result_summary_omits_full_rows():
    store = ResultStore()
    result = store.add(
        ResultSet(kind="tracks", rows=[{"id": "track-1", "large": "x" * 5000}])
    )
    summary = store.summary(result.id)
    assert "rows" not in summary
    assert summary["count"] == 1
    assert summary["result_id"] == result.id


def test_presentation_cannot_reference_unknown_result():
    with pytest.raises(ValueError, match="Unknown result"):
        ResultStore().validate_presentation(
            Presentation(component="table", result_id="forged")
        )


def test_presentation_rejects_unknown_component():
    with pytest.raises(ValidationError):
        Presentation(component="execute_js", result_id="result-1")


def test_chart_counts_are_derived_from_source_evidence():
    store = ResultStore()
    result = store.add(
        ResultSet(
            kind="genes",
            rows=[
                {
                    "id": "g1",
                    "evidence": [{"data_source": "list-a"}, {"data_source": "track-b"}],
                },
                {"id": "g2", "evidence": [{"data_source": "track-b"}]},
            ],
        )
    )
    assert store.source_counts(result.id) == [
        {"term": "list-a", "count": 1},
        {"term": "track-b", "count": 2},
    ]


def test_result_page_has_explicit_incompleteness():
    result = ResultSet(kind="genes", rows=[{"id": "g1"}], has_more=True)
    assert result.has_more
    assert result.page == 1
    with pytest.raises(ValidationError):
        ResultSet(kind="genes", rows=[], limit=101)
    with pytest.raises(ValidationError):
        ResultSet(kind="genes", rows=[], page=MAX_NUM_PAGES + 1)
