"""Generate query vectors through OpenRouter using the existing ETL model."""

import asyncio
import math

from aiohttp import ClientError
from niagads.api.common.config import QueryEmbeddingSettings
from niagads.common.core import ComponentBaseMixin
from niagads.requests.core import HttpClientSessionManager
from pydantic import FiniteFloat, TypeAdapter


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
            if "error" in payload:
                raise ValueError(f"Provider error: {payload['error']!r}")
            if len(payload["data"]) != 1:
                raise ValueError(
                    f"Expected one embedding; received {len(payload['data'])}."
                )
            item = payload["data"][0]
            if item["index"] != 0:
                raise ValueError(
                    f"Expected embedding index 0; received {item['index']!r}."
                )
            vector = TypeAdapter(list[FiniteFloat]).validate_python(
                item["embedding"], strict=True
            )
            if not vector:
                raise ValueError("Received an empty embedding vector.")
            norm = math.hypot(*vector)
            if not math.isfinite(norm) or norm == 0:
                raise ValueError(
                    f"Expected a finite, nonzero embedding norm; received {norm!r}."
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"OpenRouter query embedding validation failed (model {model}): "
                f"{type(exc).__name__}: {exc}"
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
                    raise_for_status=False,
                ) as response:
                    if response.status >= 400:
                        detail = await response.text()
                        raise RuntimeError(
                            "OpenRouter query embedding failed "
                            f"(HTTP {response.status}, model {model}): {detail}"
                        )
                    return self.normalize_embedding(await response.json(), model)
        except (ClientError, asyncio.TimeoutError) as exc:
            raise RuntimeError(
                f"OpenRouter query embedding failed (model {model}): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
