from niagads.settings.core import CustomSettings
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field


class BaseRagdocServiceSettings(CustomSettings):
    """Configuration for the document knowledgebase read API."""

    DATABASE_URI: str = Field(..., pattern=RegularExpressions.POSTGRES_URI)
