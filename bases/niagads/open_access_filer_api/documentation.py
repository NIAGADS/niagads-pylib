"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import Set

from niagads.open_access_api_common.app import OpenAPISpec, OpenAPITag
from niagads.open_access_api_common.config.core import get_settings
from niagads.open_access_api_common.types import T_PubMedID

OPEN_API_TAGS = OpenAPITag(
    name="FILER Functional Genomics Repository",
    description=(
        f"Query tracks and track data in FILER, "
        f"a functional genomics database developed by NIAGADS "
        f"with the most comprehensive harmonized, extensible, "
        f"indexed, searchable human functional genomics data collection "
        f"across >20 data sources."
    ),
    externalDocs={
        "description": "FILER Website",
        "url": "https://tf.lisanwanglab.org/FILER/",
    },
)

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

ROUTE_NAME: str = OPEN_API_TAGS.name


OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS.name,
    description=OPEN_API_TAGS.description,
    summary="NIAGADS Open Access API: FILER",
    version=get_settings().API_VERSION,
    admin_email=get_settings().ADMIN_EMAIL,
    service_url=get_settings().API_PUBLIC_URL,
    openapi_tags=[OPEN_API_TAGS],
)
