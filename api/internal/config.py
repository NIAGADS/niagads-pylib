from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_core import ValidationError
from functools import lru_cache
from os import path

ENV_FILE_PATH = f"{path.dirname(path.abspath(__file__))}/../../.env.local"
class Settings(BaseSettings):
    API_STATICDB_URL: str
    API_CACHEDB_URL: str
    GENOMICSDB_URL: str
    FILER_REQUEST_URI: str
    SESSION_SECRET: str
    
    # required by Pydantic
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH)
  


@lru_cache # memoization of functions
def get_settings():
    return Settings()
