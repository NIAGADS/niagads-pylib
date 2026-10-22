"""OpenRouter construction, isolated from domain tools and frontend transport."""

from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.retries import RetryingModel, configure_retry_client
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider


def build_model(settings: AskSettings) -> RetryingModel:
    """Use the configured chat model or OpenRouter routing identifier."""
    if not settings.model or not settings.api_key:
        raise ValueError(
            "Set ASK_MODEL to an OpenRouter chat model or router and "
            "OPENROUTER_API_KEY server-side."
        )
    provider = OpenRouterProvider(api_key=settings.api_key.get_secret_value())
    configure_retry_client(provider.client)
    return RetryingModel(OpenRouterModel(settings.model, provider=provider))
