# Settings for Open Access API microservices
from typing import Optional

from niagads.settings.core import CustomSettings


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
