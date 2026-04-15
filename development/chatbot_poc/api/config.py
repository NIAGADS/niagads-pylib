from niagads.settings.core import CustomSettings


class Settings(CustomSettings):
    """Configuration for the document knowledgebase read API."""

    DATABASE_URI: str
    API_VERSION: str = "0.1.0"
