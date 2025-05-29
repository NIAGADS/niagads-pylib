"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import List, Set

from niagads.common.types.core import T_PubMedID
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.types import (
    OpenAPISpec,
    OpenAPITag,
    OpenAPIxTagGroup,
)


OPEN_API_TAGS: List[OpenAPITag] = [
    OpenAPITag(
        name="FILER Functional Genomics Repository",
        summary="Query tracks and track data in FILER",
        description=(
            f"Query tracks and track data in FILER, "
            f"a functional genomics database developed by NIAGADS "
            f"built on a comprehensive harmonized, extensible, "
            f"indexed, searchable human functional genomics data collection "
            f"across >20 data sources."
        ),
        externalDocs={
            "description": "FILER",
            "url": "https://tf.lisanwanglab.org/FILER/",
        },
        xSortOrder=3,
    ),
    SharedOpenAPITags.ABOUT.value,
    SharedOpenAPITags.TRACK_RECORD.value,
    SharedOpenAPITags.XQTL_TRACK_RECORD.value,
    SharedOpenAPITags.TRACK_DATA.value,
    SharedOpenAPITags.RECORD_BY_ID.value,
    SharedOpenAPITags.RECORD_BY_REGION.value,
    SharedOpenAPITags.RECORD_BY_TEXT.value,
    SharedOpenAPITags.COLLECTIONS.value,
    SharedOpenAPITags.SERVICES.value,
    SharedOpenAPITags.GENOME_BROWSER.value,
    SharedOpenAPITags.LOOKUP_SERVICES.value,
]

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

ROUTE_NAME: str = OPEN_API_TAGS[0].name

FILER_TAG_GROUPS = [
    OpenAPIxTagGroup(name=ROUTE_NAME, tags=OPEN_API_TAGS, xSortOrder=40)
]

OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[0].name,
    description=OPEN_API_TAGS[0].summary,
    summary="NIAGADS Open Access API: FILER",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=OPEN_API_TAGS,
    xtag_groups=FILER_TAG_GROUPS,
)
