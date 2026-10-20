"""Generate query vectors through OpenRouter using the existing ETL model."""

import asyncio
import math

from aiohttp import ClientError
from niagads.api.common.config import QueryEmbeddingSettings
from niagads.common.core import ComponentBaseMixin
from niagads.requests.core import HttpClientSessionManager
from pydantic import FiniteFloat, TypeAdapter


class OpenRouterQueryEmbedding(ComponentBaseMixin):
    """Resolve the ETL model's provider ID and generate normalized query vectors."""

    # Match TextEmbeddingGenerator's ETL default without importing local model code.
    MODEL = "LiquidAI/LFM2.5-Embedding-350M"
    BASE_URL = "https://openrouter.ai"

    def __init__(self, settings: QueryEmbeddingSettings | None = None):
        super().__init__()
        self._settings = settings or QueryEmbeddingSettings.from_env()

    @classmethod
    def resolve_model(cls, catalog: dict) -> str:
        """Require one exact Hugging Face identity; never select a substitute."""
        if not isinstance(catalog, dict) or not isinstance(catalog.get("data"), list):
            raise RuntimeError(
                "OpenRouter returned an invalid embedding model catalog."
            )
        matches = {
            model["id"]
            for model in catalog["data"]
            if isinstance(model, dict)
            and isinstance(model.get("hugging_face_id"), str)
            and model["hugging_face_id"].casefold() == cls.MODEL.casefold()
            and isinstance(model.get("id"), str)
            and model["id"]
        }
        if len(matches) != 1:
            raise NotImplementedError(
                f"OpenRouter must advertise exactly one embedding model matching "
                f"the ETL model {cls.MODEL}; no compatible model was confirmed."
            )
        return next(iter(matches))

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
        except (KeyError, TypeError, ValueError):
            raise RuntimeError(
                "OpenRouter returned an invalid query embedding or a different model."
            ) from None
        return [value / norm for value in vector]

    async def generate(self, query: str) -> list[float]:
        """Embed raw search text remotely, using the ETL's normalized-vector convention."""
        if not query.strip():
            raise ValueError("A nonempty semantic search query is required.")
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
                async with session.get(
                    "/api/v1/embeddings/models", headers=headers
                ) as response:
                    model = self.resolve_model(await response.json())
                async with session.post(
                    "/api/v1/embeddings",
                    headers=headers,
                    json={"model": model, "input": query, "encoding_format": "float"},
                ) as response:
                    return self.normalize_embedding(await response.json(), model)
        except (ClientError, asyncio.TimeoutError):
            raise RuntimeError(
                "OpenRouter query embedding failed; check provider access, credentials, "
                "and model availability."
            ) from None
