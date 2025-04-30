# Settings for Open Access API microservices
from typing import Optional

# from niagads.database_models.track.properties import TrackDataStore
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.enums.core import CaseInsensitiveEnum
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class CustomSettings(BaseSettings):
    # default file is .env in current path
    model_config = SettingsConfigDict(env_file=".env")

    @classmethod
    @lru_cache()
    def get(cls):
        """Get application configuration from env file

        checks for a `SERVICE_ENV` environmental variable
        set to `dev` or `prod
        and load configuration from appropriate `{SERVICE_ENV}.env` file
        """
        env = os.getenv("SERVICE_ENV", None)
        if env is not None:
            return cls(_env_file=f"{str(env)}.env")
        return cls()


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
