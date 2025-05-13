"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import Set

from niagads.common.types.core import T_PubMedID
from niagads.open_access_api_common.app import OpenAPISpec, OpenAPITag
from niagads.open_access_api_common.config.core import Settings


OPEN_API_TAGS = OpenAPITag(
    name="Alzheimer's Genomics Database",
    description=(
        f"Query annotated AD/ADRD-genetic evidence from GWAS summary statistics "
        f"and ADSP variant annotations from the NIAGADS repository "
        f"that have compiled in the context of summary gene, variants, and genomic regions "
        f"in support of the NIAGADS Alzheimer's GenomicsDB, "
        f"an interactive knowledgebase for AD genetics that provides a platform for data "
        f"sharing, discovery, and analysis."
    ),
    externalDocs={
        "description": "GenomicsDB Website",
        "url": "https://www.niagads.org/genomics",
    },
)

PUBMED_IDS: Set[T_PubMedID] = ["PMID:37881831"]

ROUTE_NAME: str = OPEN_API_TAGS.name


OPEN_API_SPEC = OpenAPISpec(
    title=OPEN_API_TAGS.name,
    description=OPEN_API_TAGS.description,
    summary="NIAGADS Open Access API: GenomicsDB",
    version=Settings.from_env().API_VERSION,
    admin_email=Settings.from_env().ADMIN_EMAIL,
    service_url=Settings.from_env().API_PUBLIC_URL,
    openapi_tags=[OPEN_API_TAGS],
)
