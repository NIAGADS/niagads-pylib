"""Generate query vectors through OpenRouter using the existing ETL model."""

import asyncio
import math

from aiohttp import ClientError
from niagads.api.common.config import QueryEmbeddingSettings
from niagads.common.core import ComponentBaseMixin
from niagads.requests.core import HttpClientSessionManager
from pydantic import FiniteFloat, TypeAdapter


class QueryEmbeddingError(RuntimeError, ComponentBaseMixin):
    """Preserve embedding failures and provider references for internal callers."""

    def __init__(self, message: str, request_id: str | None = None):
        RuntimeError.__init__(self, message)
        self.request_id = request_id


class OpenRouterQueryEmbedding(ComponentBaseMixin):
    """Generate query vectors using the configured, restricted embedding model."""

    BASE_URL = "https://openrouter.ai"

    def __init__(self, settings: QueryEmbeddingSettings | None = None):
        super().__init__()
        self._settings = settings or QueryEmbeddingSettings.from_env()

    @staticmethod
    def normalize_embedding(payload: dict, model: str) -> list[float]:
        """Validate the selected model's one-vector response and unit-normalize it."""
        try:
            if payload["model"] != model or len(payload["data"]) != 1:
                raise ValueError
            item = payload["data"][0]
            if item["index"] != 0:
                raise ValueError
            vector = TypeAdapter(list[FiniteFloat]).validate_python(
                item["embedding"], strict=True
            )
            norm = math.hypot(*vector)
            if not vector or not math.isfinite(norm) or norm == 0:
                raise ValueError
        except (KeyError, TypeError, ValueError) as exc:
            raise QueryEmbeddingError(
                "OpenRouter returned an invalid query embedding or a different model."
            ) from exc
        return [value / norm for value in vector]

    async def generate(self, query: str) -> list[float]:
        """Embed raw search text remotely, using the ETL's normalized-vector convention."""
        if not query.strip():
            raise ValueError("A nonempty semantic search query is required.")
        model = self._settings.OPENROUTER_EMBEDDING_MODEL
        headers = {
            "Authorization": (
                f"Bearer {self._settings.OPENROUTER_API_KEY.get_secret_value()}"
            )
        }
        try:
            async with HttpClientSessionManager(
                self.BASE_URL, timeout=self._settings.OPENROUTER_EMBEDDING_TIMEOUT
            ) as manager:
                session = await manager()
                async with session.post(
                    "/api/v1/embeddings",
                    headers=headers,
                    json={"model": model, "input": query, "encoding_format": "float"},
                ) as response:
                    request_id = response.headers.get("x-request-id")
                    try:
                        payload = await response.json()
                        return self.normalize_embedding(payload, model)
                    except (ValueError, QueryEmbeddingError) as exc:
                        raise QueryEmbeddingError(
                            "OpenRouter returned an invalid query embedding.",
                            request_id,
                        ) from exc
        except (ClientError, asyncio.TimeoutError) as exc:
            raise QueryEmbeddingError(
                "OpenRouter query embedding failed; check provider access, credentials, "
                "and model availability."
            ) from exc
