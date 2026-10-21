"""Server-side settings for the constrained prototype."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AskSettings(BaseSettings):
    """Finite request budgets; provider credentials never enter browser config."""

    model_config = SettingsConfigDict(
        env_prefix="ASK_", env_file=".env", extra="ignore"
    )

    model: str | None = None
    api_key: SecretStr | None = Field(
        default=None, validation_alias="OPENROUTER_API_KEY"
    )
    model_requests: int = Field(default=8, ge=1, le=12)
    tool_calls: int = Field(default=12, ge=1, le=20)
    api_timeout: float = Field(default=20, gt=0, le=30)
    deadline: float = Field(default=90, gt=0, le=120)
    max_bar_categories: int = Field(default=7, ge=1)
    telemetry: bool = False
    capture_content: bool = False
