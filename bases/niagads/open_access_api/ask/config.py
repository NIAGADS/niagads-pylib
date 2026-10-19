"""Server-side settings for the constrained prototype."""

from pydantic import Field, SecretStr, field_validator
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
    telemetry: bool = False
    capture_content: bool = False

    @field_validator("model")
    @classmethod
    def require_free_model(cls, value: str | None) -> str | None:
        """Never silently switch to paid models or free-model routers."""
        if value is not None and not value.endswith(":free"):
            raise ValueError(
                "Configure an explicit tool-capable :free OpenRouter model"
            )
        return value
