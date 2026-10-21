# Settings for Open Access API microservices
from typing import Literal, Optional

from niagads.settings.core import CustomSettings
from pydantic import Field, SecretStr


class Settings(CustomSettings):
    DATABASE_URI: str  # application db (e.g., GenomicsDB or FILER metadata cache)
    CACHE_DB_URI: str  # in memory cache db

    API_PUBLIC_URL: str = "http://localhost:8000"  # public facing URL for the API

    ADMIN_EMAIL: str = "betatesting@niagads.org"
    CACHE_TTL: str = "DEFAULT"  # Cache time to life

    FILER_REQUEST_URL: Optional[str] = None  # FILER API base URL
    XQTL_REQUEST_URL: Optional[str] = None  # FILER API base URL

    IGV_BROWSER_INFO_URL: str = "/record"

    # FIXME: required for correlation middleware; not currently in use
    SESSION_SECRET: Optional[str] = None

    MAX_SPAN_SIZE: int = 50000

    API_VERSION: Optional[str] = "0.0.1"
    SUPPORT_EMAIL: str = "betatesting@niagads.org"

    LTS: bool = True

    def get_major_version(self):
        if self.LTS:
            return "lts"

        return f"v{self.API_VERSION.split('.')[0]}"


class QueryEmbeddingSettings(CustomSettings):
    """OpenRouter credentials required only when a semantic query is embedded."""

    OPENROUTER_API_KEY: SecretStr
    OPENROUTER_EMBEDDING_MODEL: Literal["liquid/lfm-2.5-embedding-350m:free"] = (
        "liquid/lfm-2.5-embedding-350m:free"
    )
    OPENROUTER_EMBEDDING_TIMEOUT: float = Field(default=20, gt=0, le=30)
