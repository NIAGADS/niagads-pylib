# Settings for Open Access API microservices
from typing import Optional

# from niagads.database_models.track.properties import TrackDataStore
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class CustomSettings(BaseSettings):
    # default file is .env in current path
    model_config = SettingsConfigDict(env_file=".env", extra='allow')

    @model_validator(mode='after')
    def remove_extra_fields(self):
        """ basically allow an .env file to have additional fields but don't store them"""
        if self.__pydantic_extra__:
            self.__pydantic_extra__ = None
        return self
    
    # TODO add custom setting source so can throw error when .env file does not exist
    # see https://docs.pydantic.dev/latest/concepts/pydantic_settings/#adding-sources

    @classmethod
    @lru_cache()
    def from_env(cls):
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
