"""Coarse intent does not couple the agent to a frontend component registry."""

import pytest
from niagads.open_access_api.ask.contracts import (
    AskResponse,
    PresentationIntent,
    ResultSet,
)
from niagads.open_access_api.ask.results import ResultStore
from pydantic import ValidationError


def test_unknown_plot_types_are_preferences_not_server_capabilities():
    store = ResultStore()
    result = store.add(
        ResultSet(entity="gene", annotation="report", rows=[{"id": "g1"}])
    )
    intent = PresentationIntent(
        result_id=result.id,
        view="plot",
        plot_type="future_plot",
        x="position",
        y="neg_log10_pvalue",
    )
    assert store.validate_presentation(intent) is intent


def test_forged_references_and_executable_ui_props_are_rejected():
    with pytest.raises(RuntimeError, match="Unknown result"):
        ResultStore().validate_presentation(
            PresentationIntent(result_id="forged", view="table")
        )
    with pytest.raises(ValidationError):
        PresentationIntent(
            result_id="r1", view="table", columns=["id"], onClick="run()"
        )


def test_summary_has_data_fields_without_ui_capabilities():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="track", annotation="report", rows=[{"id": "t1", "name": "Track"}]
        )
    )
    summary = store.summary(result.id)
    assert summary["fields"] == ["id", "name"]
    assert "presentations" not in summary
    assert "columns" not in summary


def test_wire_contract_no_longer_contains_chart_policy():
    data = AskResponse().model_dump(mode="json")
    assert data["version"] == 4
    assert "max_bar_categories" not in data
