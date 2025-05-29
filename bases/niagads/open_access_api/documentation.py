"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import List, Set

from niagads.common.types.core import T_PubMedID
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.types import OpenAPISpec, OpenAPITag


OPEN_API_TAGS: List[OpenAPITag] = [
    OpenAPITag(
        name="NIAGADS Open Access API",
        summary="Query or browse data from NIAGADS Open Access Resources",
        description=(
            f"NIAGADS is a collaborative agreement between the National Institute on Aging "
            f"and the University of Pennsylvania that stores and distributes genetics "
            f"and genomics data from studies on Alzheimer’s disease, related dementias, "
            f"and aging to qualified researchers globally. NIAGADS Open Access is a collection of unrestricted "
            f"data and annotation resources made available to the public."
        ),
        externalDocs={
            "description": "NIAGADS",
            "url": "https://www.niagads.org",
        },
        xSortOrder=1,
    ),
    SharedOpenAPITags.ABOUT.value,
    SharedOpenAPITags.SPECIFICATION.value,
]

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

ROUTE_NAME: str = OPEN_API_TAGS[0].name

OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[0].name,
    description=OPEN_API_TAGS[0].summary,
    summary="NIAGADS Open Access API",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=OPEN_API_TAGS,
)
