"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import List, Set

from niagads.common.types import T_PubMedID
from niagads.api_common.constants import (
    SharedOpenAPITags,
    SharedOpenAPIxTagGroups,
)
from niagads.api_common.config import Settings
from niagads.api_common.app.openapi import (
    OpenAPISpec,
    OpenAPITag,
    OpenAPIxTagGroup,
)

APP_NAMESPACE = "FILER"


OPEN_API_TAGS: List[OpenAPITag] = [
    OpenAPITag(
        name=APP_NAMESPACE,
        description="sub-API namespace",
        x_sort_order=0,
    ),
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
        x_sort_order=3,
    ),
    SharedOpenAPITags.DOCUMENTATION.value,
    SharedOpenAPITags.TRACK_RECORD.value,
    # SharedOpenAPITags.XQTL_TRACK_RECORD.value,
    SharedOpenAPITags.TRACK_DATA.value,
    SharedOpenAPITags.COLLECTIONS.value,
    SharedOpenAPITags.GENOME_BROWSER.value,
    SharedOpenAPITags.ONTOLOGIES.value,
    SharedOpenAPITags.RECORD_SEARCH.value,
]

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

APP_NAME: str = OPEN_API_TAGS[1].name

BASE_TAGS = [APP_NAMESPACE, APP_NAME]


FILER_TAG_GROUPS = [
    OpenAPIxTagGroup(name="Knowledge Bases", tags=[OPEN_API_TAGS[1]], x_sort_order=0)
] + SharedOpenAPIxTagGroups.list()


OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[1].name,
    description=OPEN_API_TAGS[1].summary,
    summary="NIAGADS Open Access API: FILER",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=OPEN_API_TAGS,
    xtag_groups=FILER_TAG_GROUPS,
)
