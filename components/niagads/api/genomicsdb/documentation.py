"""OpenAPI and related metadata for the Open Access GenomicsDB microservice."""

from typing import List, Set

from niagads.common.types import T_PubMedID
from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.config import Settings
from niagads.api.common.app.openapi import (
    OpenAPISpec,
    OpenAPITag,
    OpenAPIxTagGroup,
)

APP_NAMESPACE = "Genomics"

OPEN_API_TAGS: List[OpenAPITag] = [
    OpenAPITag(
        name=APP_NAMESPACE,
        description=(
            f"Query annotated AD/ADRD-genetic evidence from GWAS summary statistics "
            f"and ADSP variant annotations from the NIAGADS repository "
            f"that have compiled in the context of summary gene, variants, and genomic regions "
            f"in support of the NIAGADS Alzheimer's GenomicsDB, "
            f"an interactive knowledgebase for AD genetics that provides a platform for data "
            f"sharing, discovery, and analysis."
        ),
        x_sort_order=0,
    ),
] + SharedOpenAPITags.list()


PUBMED_IDS: Set[T_PubMedID] = ["PMID:37881831"]

APP_NAME: str = OPEN_API_TAGS[0].name

BASE_TAGS = [APP_NAMESPACE]

OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS[0].name,
    description=OPEN_API_TAGS[0].description,
    summary="NIAGADS Open Access API: GenomicsDB",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=SharedOpenAPITags.list(),
)
