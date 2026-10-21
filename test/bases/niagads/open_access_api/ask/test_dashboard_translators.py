"""Dashboard selections never supply or rewrite authoritative data."""

import pytest
from niagads.open_access_api.ask.contracts import AskResponse, ResultSet
from niagads.open_access_api.ask.presentations import (
    AssociationCountsPresentation,
    CategoryCountsPresentation,
    CategoryParameters,
    TableParameters,
    TablePresentation,
)
from niagads.open_access_api.ask.results import ResultStore
from pydantic import ValidationError


def test_registry_advertises_actual_fields_without_full_records():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="track",
            annotation="report",
            rows=[{"id": "t1", "name": "Study", "is_download_only": False}],
        )
    )
    summary = store.summary(result.id)
    assert "rows" not in summary
    table = next(
        p for p in summary["presentations"] if p["translator"] == "track_records_table"
    )
    assert "id" in table["columns"]
    assert "is_download_only" in table["group_by"]


def test_table_cannot_hide_identifier_or_request_unknown_fields():
    store = ResultStore()
    result = store.add(
        ResultSet(entity="track", annotation="report", rows=[{"id": "t1"}])
    )
    for columns in (["name"], ["id", "execute_js"]):
        with pytest.raises(ValueError):
            store.validate_presentation(
                TablePresentation(
                    translator="track_records_table",
                    result_id=result.id,
                    parameters=TableParameters(columns=columns),
                )
            )


def test_translator_requires_compatible_result_and_parameter_types():
    store = ResultStore()
    result = store.add(ResultSet(entity="gene", annotation=None, rows=[]))
    with pytest.raises(ValueError):
        store.validate_presentation(
            TablePresentation(translator="gene_records_table", result_id=result.id)
        )
    with pytest.raises(ValidationError):
        CategoryCountsPresentation(
            result_id=result.id,
            parameters={"group_by": "match_type", "callback": "run()"},
        )


def test_api_summary_preserves_counts_and_rejects_malformed_values():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="variant",
            annotation="associations",
            content="summary",
            rows=[{"track": "t1", "num_associations": 1200}],
        )
    )
    store.validate_presentation(AssociationCountsPresentation(result_id=result.id))
    assert store.get(result.id).rows[0]["num_associations"] == 1200
    for value in (-1, True, "1200", 1.5):
        result.rows[0]["num_associations"] = value
        with pytest.raises(ValueError):
            store.validate_presentation(
                AssociationCountsPresentation(result_id=result.id)
            )


def test_category_grouping_is_registered_not_an_arbitrary_path():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="track", annotation="report", rows=[{"id": "t1", "name": "Study"}]
        )
    )
    for field in ("id", "name", "provenance.anything"):
        with pytest.raises(ValueError):
            store.validate_presentation(
                CategoryCountsPresentation(
                    result_id=result.id, parameters=CategoryParameters(group_by=field)
                )
            )


def test_envelope_version_and_bar_limit_are_explicit():
    assert AskResponse().version == 3
    assert AskResponse().max_bar_categories == 7
    with pytest.raises(ValidationError):
        AskResponse(version=2)
    with pytest.raises(ValidationError):
        AskResponse(max_bar_categories=0)
