"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import Set

from niagads.common.types.core import T_PubMedID
from niagads.open_access_api_common.app import OpenAPISpec, OpenAPITag
from niagads.open_access_api_common.config.core import Settings

from niagads.settings.core import get_service_environment


OPEN_API_TAGS = OpenAPITag(
    name="NIAGADS Open Access API",
    description=(f"Query or browse data from NIAGADS Open Access Resources"),
    externalDocs={
        "description": "NIAGADS Home",
        "url": "https://www.niagads.org",
    },
)

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

ROUTE_NAME: str = OPEN_API_TAGS.name


OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS.name,
    description=OPEN_API_TAGS.description,
    summary="NIAGADS Open Access API",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=[OPEN_API_TAGS],
)
