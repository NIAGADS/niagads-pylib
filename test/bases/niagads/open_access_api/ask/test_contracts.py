"""Validate authoritative results independently of database/provider access."""

import pytest
from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.open_access_api.ask.contracts import (
    Presentation,
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
    with pytest.raises(ValueError, match="Unknown result"):
        ResultStore().validate_presentation(
            Presentation(component="table", result_id="forged")
        )


def test_presentation_rejects_unknown_component():
    with pytest.raises(ValidationError):
        Presentation(component="execute_js", result_id="result-1")


def test_summary_preview_preserves_api_association_counts():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation="associations",
            content="summary",
            rows=[
                {"track": "track-a", "traits": {}, "num_associations": 1200}
            ],
        )
    )
    summary = store.summary(result.id)
    assert summary["content"] == "summary"
    assert summary["preview"] == [
        {"track": "track-a", "num_associations": 1200}
    ]
    store.validate_presentation(
        Presentation(component="association_source_bar", result_id=result.id)
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
        ResultSet(
            entity="gene", annotation="report", rows=[], page=MAX_NUM_PAGES + 1
        )


def test_chart_requires_an_association_summary():
    store = ResultStore()
    for entity, annotation, allowed in (
        ("gene", "report", False),
        ("variant", "report", False),
        ("gene", "structure", False),
        ("gene", None, False),
        ("variant", "associations", True),
        ("region", "associations", True),
    ):
        result = store.add(
            ResultSet(entity=entity, annotation=annotation, content="summary")
        )
        presentation = Presentation(
            component="association_source_bar", result_id=result.id
        )
        if allowed:
            store.validate_presentation(presentation)
        else:
            with pytest.raises(ValueError, match="association summary"):
                store.validate_presentation(presentation)


def test_result_serializes_entity_and_annotation_separately():
    result = ResultSet(entity="GENE", annotation="ASSOCIATIONS")
    data = result.model_dump(mode="json")
    assert data["entity"] == "gene"
    assert data["annotation"] == "associations"
    assert "kind" not in data
    with pytest.raises(ValidationError):
        ResultSet(entity="gene", annotation="unknown")


def test_chart_rejects_full_association_records():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation="associations",
            content="full",
            rows=[{"variant": "rs1", "track": "track-a"}],
        )
    )
    with pytest.raises(ValueError, match="association summary"):
        store.validate_presentation(
            Presentation(
                component="association_source_bar", result_id=result.id
            )
        )
