"""OpenRouter construction, isolated from domain tools and frontend transport."""

from niagads.open_access_api.ask.config import AskSettings
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider


def build_model(settings: AskSettings) -> OpenRouterModel:
    """Use the explicitly selected free model without provider/model fallback."""
    if not settings.model or not settings.api_key:
        raise ValueError(
            "Set ASK_MODEL to a tool-capable :free model and OPENROUTER_API_KEY server-side."
        )
    return OpenRouterModel(
        settings.model,
        provider=OpenRouterProvider(api_key=settings.api_key.get_secret_value()),
    )
