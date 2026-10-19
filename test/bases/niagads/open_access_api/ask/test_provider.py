"""Provider construction is isolated and never falls back to another model."""

import pytest
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.provider import build_model


def test_provider_requires_explicit_model_and_server_key():
    with pytest.raises(ValueError, match="ASK_MODEL"):
        build_model(AskSettings())


def test_provider_retains_exact_free_model_without_making_a_request():
    model = build_model(
        AskSettings(
            model="example/test-model:free", OPENROUTER_API_KEY="test-only-placeholder"
        )
    )
    assert model.model_name == "example/test-model:free"
    assert model.system == "openrouter"
