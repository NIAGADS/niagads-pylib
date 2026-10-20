"""Construct the provider from the configured ASK settings."""

import pytest
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.provider import build_model


def test_configured_provider():
    settings = AskSettings()
    model = build_model(settings)

    assert model.model_name == settings.model
    assert model.system == "openrouter"


@pytest.mark.parametrize("missing_field", ["model", "api_key"])
def test_provider_requires_model_and_key(missing_field):
    settings = AskSettings().model_copy(update={missing_field: None})

    with pytest.raises(ValueError, match="ASK_MODEL"):
        build_model(settings)
