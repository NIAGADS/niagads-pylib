from niagads.enums.core import CaseInsensitiveEnum
from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class CustomSettings(BaseSettings):
    # default file is .env in current path
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @model_validator(mode="after")
    def remove_extra_fields(self):
        """basically allow an .env file to have additional fields but don't store them"""
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
        env_file = ".env"
        env = os.getenv("SERVICE_ENV", None)
        try:
            if env is not None:
                env_file = f"{str(env)}.env"
                return cls(_env_file=env_file)
            return cls()
        except (ValidationError, ValueError) as e:
            error_details = "; ".join(
                f"{err['loc'][0]}: {err['msg']}" for err in e.errors()
            )
            raise ValueError(
                f"Configuration error(s) found in the environmental settings: \n"
                f"{error_details}\n"
                f"Please check your `{env_file}` file for missing or invalid values."
            ) from None


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
