"""OpenAPI and related metadata for the Open Access GenomicsDB microservice."""

from typing import List, Set

from niagads.common.types.core import T_PubMedID
from niagads.open_access_api_common.config.constants import (
    SharedOpenAPITags,
    SharedOpenAPIxTagGroups,
)
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.types import (
    OpenAPISpec,
    OpenAPITag,
    OpenAPIxTagGroup,
)

APP_NAMESPACE = "Genomics"

OPEN_API_TAGS: List[OpenAPITag] = [
    OpenAPITag(
        name=APP_NAMESPACE,
        description="sub-API namespace",
        xTraitTag=True,
        xSortOrder=0,
    ),
    OpenAPITag(
        name="Alzheimers Genomics Database",
        summary="Query annotated AD/ADRD-genetic evidence from GWAS summary statistics and ADSP variant annotations",
        description=(
            f"Query annotated AD/ADRD-genetic evidence from GWAS summary statistics "
            f"and ADSP variant annotations from the NIAGADS repository "
            f"that have compiled in the context of summary gene, variants, and genomic regions "
            f"in support of the NIAGADS Alzheimer's GenomicsDB, "
            f"an interactive knowledgebase for AD genetics that provides a platform for data "
            f"sharing, discovery, and analysis."
        ),
        externalDocs={
            "description": "Alzheimer's GenomicsDB",
            "url": "https://www.niagads.org/genomics",
        },
        xSortOrder=2,
        # xTraitTag=True,
    ),
    SharedOpenAPITags.DOCUMENTATION.value,
    SharedOpenAPITags.GENE_RECORD.value,
    SharedOpenAPITags.VARIANT_RECORD.value,
    SharedOpenAPITags.XQTL_TRACK_RECORD.value,
    SharedOpenAPITags.GWAS_TRACK_RECORD.value,
    SharedOpenAPITags.TRACK_DATA.value,
    SharedOpenAPITags.COLLECTIONS.value,
    SharedOpenAPITags.GENOME_BROWSER.value,
    # SharedOpenAPITags.LOCUSZOOOM.value,
]


PUBMED_IDS: Set[T_PubMedID] = ["PMID:37881831"]

APP_NAME: str = OPEN_API_TAGS[1].name

BASE_TAGS = [APP_NAMESPACE, APP_NAME]

GENOMICS_TAG_GROUPS = [
    OpenAPIxTagGroup(name=APP_NAME, tags=OPEN_API_TAGS, xSortOrder=20)
] + SharedOpenAPIxTagGroups.list()

OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[1].name,
    description=OPEN_API_TAGS[1].summary,
    summary="NIAGADS Open Access API: GenomicsDB",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=OPEN_API_TAGS,
    xtag_groups=GENOMICS_TAG_GROUPS,
)
