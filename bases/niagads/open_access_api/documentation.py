"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import List, Set

from niagads.api_common.app.openapi import OpenAPISpec, OpenAPITag
from niagads.api_common.config import Settings
from niagads.api_common.constants import SharedOpenAPITags
from niagads.common.types import T_PubMedID

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
        x_sort_order=1,
    ),
    SharedOpenAPITags.STATUS.value,
]

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

APP_NAME: str = OPEN_API_TAGS[0].name

OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[0].name,
    description=OPEN_API_TAGS[0].summary,
    summary="NIAGADS Open Access API",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=[SharedOpenAPITags.STATUS.value],
)
