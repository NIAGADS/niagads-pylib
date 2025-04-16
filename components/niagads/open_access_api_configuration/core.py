# Settings for Open Access API microservices
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    API_APP_DB_URI: str  # application db (e.g., GenomicsDB or FILER metadata cache)
    API_CACHE_DB_URI: str  # in memory cache db

    API_PUBLIC_URL: str = "http://localhost:8000"  # public facing URL for the API

    ADMIN_EMAIL: str = "betatesting@niagads.org"
    CACHE_TTL: str = "DEFAULT"  # Cache time to life

    FILER_REQUEST_URL: Optional[str] = None  # FILER API base URL

    IGV_BROWSER_INFO_URL: str = "/record"

    # FIXME: required for correlation middleware; not currently in use
    SESSION_SECRET: Optional[str] = None

    # default file is .env in current path
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    """Get application configuration from env file

    checks for a `SERVICE_ENV` environmental variable
    set to `dev` or `prod
    and load configuration from appropriate `{SERVICE_ENV}.env` file
    """
    match os.getenv("SERVICE_ENV", None):
        case "DEV" | "dev" | "DEVELOPMENT" | "development":
            return Settings(_env_file="dev.env")  # overrides default env file
        case "PROD" | "prod" | "PRODUCTION" | "production":
            return Settings(_env_file="prod.env")
        case _:
            return Settings()
