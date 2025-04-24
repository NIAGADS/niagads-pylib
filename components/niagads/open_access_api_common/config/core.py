# Settings for Open Access API microservices
from typing import Optional

# from niagads.database_models.track.properties import TrackDataStore
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.enums.core import CaseInsensitiveEnum
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    APP_DB_URI: str  # application db (e.g., GenomicsDB or FILER metadata cache)
    CACHE_DB_URI: str  # in memory cache db

    DATA_STORE: TrackDataStore

    API_PUBLIC_URL: str = "http://localhost:8000"  # public facing URL for the API

    ADMIN_EMAIL: str = "betatesting@niagads.org"
    CACHE_TTL: str = "DEFAULT"  # Cache time to life

    EXTERNAL_REQUEST_URL: Optional[str] = None  # FILER API base URL

    IGV_BROWSER_INFO_URL: str = "/record"

    # FIXME: required for correlation middleware; not currently in use
    SESSION_SECRET: Optional[str] = None

    API_VERSION: str

    # default file is .env in current path
    model_config = SettingsConfigDict(env_file=".env")


class ServiceEnvironment(CaseInsensitiveEnum):
    DEV = "dev"
    PROD = "prod"
    TEST = "test"


def get_service_environment() -> ServiceEnvironment:
    """Get service environment from env file

    checks for a `SERVICE_ENV` environmental variable
    set to a variation on `dev` or `prod` or `test`
    """
    return ServiceEnvironment(os.getenv("SERVICE_ENV", "dev"))


@lru_cache
def get_settings():
    """Get application configuration from env file

    checks for a `SERVICE_ENV` environmental variable
    set to `dev` or `prod
    and load configuration from appropriate `{SERVICE_ENV}.env` file
    """
    env = os.getenv("SERVICE_ENV", None)
    if env is not None:
        return Settings(_env_file=f"{str(env)}.env")
    return Settings()
