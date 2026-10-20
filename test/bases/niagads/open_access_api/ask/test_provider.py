"""Provider construction is isolated and never falls back to another model."""

import pytest
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.provider import build_model


def test_provider_requires_explicit_model_and_server_key():
    with pytest.raises(ValueError, match="ASK_MODEL"):
        build_model(AskSettings())


@pytest.mark.parametrize(
    "model_id",
    [
        "openrouter/free",
        "openrouter/auto",
        "example/test-model:free",
        "example/test-model",
    ],
)
def test_provider_accepts_chat_models_and_routing_without_making_a_request(model_id):
    model = build_model(
        AskSettings(model=model_id, OPENROUTER_API_KEY="test-only-placeholder")
    )
    assert model.model_name == model_id
    assert model.system == "openrouter"
