"""Validate authoritative results independently of database/provider access."""

import pytest
from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.open_access_api.ask.contracts import (
    PresentationIntent,
    ResultSet,
)
from niagads.open_access_api.ask.results import ResultStore
from pydantic import ValidationError


def test_result_summary_omits_full_rows():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="track",
            annotation="report",
            rows=[{"id": "track-1", "large": "x" * 5000}],
        )
    )
    summary = store.summary(result.id)
    assert "rows" not in summary
    assert summary["count"] == 1
    assert summary["result_id"] == result.id


def test_presentation_cannot_reference_unknown_result():
    with pytest.raises(RuntimeError, match="Unknown result"):
        ResultStore().validate_presentation(
            PresentationIntent(view="table", result_id="forged")
        )


def test_presentation_rejects_unknown_view():
    with pytest.raises(ValidationError):
        PresentationIntent(view="execute_js", result_id="result-1")


def test_summary_preview_preserves_api_association_counts():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation="associations",
            content="summary",
            rows=[{"track": "track-a", "traits": {}, "num_associations": 1200}],
        )
    )
    summary = store.summary(result.id)
    assert summary["content"] == "summary"
    assert summary["preview"] == [{"track": "track-a", "num_associations": 1200}]
    store.validate_presentation(
        PresentationIntent(result_id=result.id, view="plot", plot_type="bar")
    )


def test_result_page_has_explicit_incompleteness():
    result = ResultSet(
        entity="gene", annotation="report", rows=[{"id": "g1"}], has_more=True
    )
    assert result.has_more
    assert result.page == 1
    with pytest.raises(ValidationError):
        ResultSet(entity="gene", annotation="report", rows=[], limit=101)
    with pytest.raises(ValidationError):
        ResultSet(entity="gene", annotation="report", rows=[], page=MAX_NUM_PAGES + 1)


def test_presentation_preferences_do_not_enforce_ui_capabilities():
    store = ResultStore()
    for entity, annotation in (
        ("gene", "report"),
        ("gene", "structure"),
        ("variant", "associations"),
    ):
        result = store.add(ResultSet(entity=entity, annotation=annotation))
        intent = PresentationIntent(
            result_id=result.id, view="plot", plot_type="new_chart"
        )
        assert store.validate_presentation(intent) is intent


def test_result_serializes_entity_and_annotation_separately():
    result = ResultSet(entity="GENE", annotation="ASSOCIATIONS")
    data = result.model_dump(mode="json")
    assert data["entity"] == "gene"
    assert data["annotation"] == "associations"
    assert "kind" not in data
    with pytest.raises(ValidationError):
        ResultSet(entity="gene", annotation="unknown")


def test_plot_intent_preserves_reference_without_transforming_full_records():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation="associations",
            rows=[{"variant": "rs1", "track": "track-a"}],
        )
    )
    store.validate_presentation(
        PresentationIntent(result_id=result.id, view="plot", plot_type="bar")
    )
    assert store.get(result.id).rows == [{"variant": "rs1", "track": "track-a"}]
