"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import List, Set

from niagads.api.common.app.openapi import OpenAPISpec, OpenAPITag, OpenAPIxTagGroup
from niagads.api.common.config import Settings
from niagads.api.common.constants import SharedOpenAPITags
from niagads.common.types import T_PubMedID

APP_NAMESPACE = "FILER"


OPEN_API_TAGS: List[OpenAPITag] = [
    OpenAPITag(
        name=APP_NAMESPACE,
        description=(
            f"Query tracks and track data in FILER, "
            f"a functional genomics database developed by NIAGADS "
            f"built on a comprehensive harmonized, extensible, "
            f"indexed, searchable human functional genomics data collection "
            f"across >20 data sources."
        ),
        x_sort_order=0,
    ),
] + SharedOpenAPITags.list()

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

APP_NAME: str = OPEN_API_TAGS[0].name

BASE_TAGS = [APP_NAMESPACE]


OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[0].name,
    description=OPEN_API_TAGS[0].description,
    summary="NIAGADS Open Access API: FILER",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=OPEN_API_TAGS,
)
