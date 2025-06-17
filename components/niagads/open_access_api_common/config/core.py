# Settings for Open Access API microservices
from typing import Optional

# from niagads.database_models.track.properties import TrackDataStore
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.settings.core import CustomSettings


class Settings(CustomSettings):
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

    LTS: bool = True

    def get_major_version(self):
        if self.LTS:
            return "lts"

        return f"v{self.API_VERSION.split('.')[0]}"
