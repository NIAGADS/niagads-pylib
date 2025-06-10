# http client
from enum import Enum
from typing import List

from niagads.open_access_api_common.types import OpenAPITag, OpenAPIxTagGroup
from pydantic import BaseModel


HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 10

# Responses

RESPONSES = {
    404: {"description": "Record not found"},
    422: {"description": "Parameter Validation Error"},
    429: {"description": "Too many requests"},
}


# regular expressions
SHARD_PATTERN = r"chr(\d{1,2}|[XYM]|MT)"

# default values
DEFAULT_NULL_STRING = "NA"


class SharedOpenAPITags(Enum):
    DOCUMENTATION = OpenAPITag(
        name="Documentation",
        description="general information and over statistics about the NIAGADS Open Access resources queried by this API, including lookups for data descriptors",
        xSortOrder=10,
        xDisplayName="Resource Information",
    )
    TRACK_RECORD = OpenAPITag(
        name="Metadata",
        description="endpoints that retrieve track metadata",
        xSortOrder=20,
        xDisplayName="Track Metdata",
    )
    XQTL_TRACK_RECORD = OpenAPITag(
        name="QTL",
        description="endpoints that retrieve xQTL track data or metadata",
        xSortOrder=21,
        xDisplayName="xQTLs",
    )
    GWAS_TRACK_RECORD = OpenAPITag(
        name="SumStats",
        description="endpoints that retrieve GWAS summary statistics track data or metadata",
        xSortOrder=22,
        xDisplayName="GWAS Summary Statistics",
    )
    GENE_RECORD = OpenAPITag(
        name="Gene",
        description="endpoints that retrieve gene-specific annotations",
        xSortOrder=11,
        xDisplayName="Genes",
    )
    VARIANT_RECORD = OpenAPITag(
        name="Variant",
        description="endpoints that retrieve variant-specific annotations",
        xSortOrder=12,
        xDisplayName="Variants",
    )
    TRACK_DATA = OpenAPITag(
        name="Track Data Retrieval",
        description="endpoints that retrieve track data",
        xTraitTag=False,
        xSortOrder=13,
    )
    COLLECTIONS = OpenAPITag(
        name="Collection",
        description="endpoints that retrieve curated lists of records",
        xSortOrder=19,
        xDisplayName="Collections",
    )
    GENOME_BROWSER = OpenAPITag(
        name="Browser",
        description="service endpoints generating configuration files, data adapters, and search services for NIAGADS Genome Browser Tracks",
        xSortOrder=41,
        xDisplayName="Genome Browser",
    )
    LOCUSZOOM = OpenAPITag(
        name="LocusZoom",
        description="service endpoints generating for NIAGADS LocusZoom data adapters",
        xSortOrder=42,
    )
    LOOKUP_SERVICES = OpenAPITag(
        name="Lookups",
        description="service endpoints that provide quick record lookups based on relational data (e.g., root shard for sharded data track)",
        xSortOrder=43,
        xDisplayName="Lookup Services",
    )
    PAGINATION = OpenAPITag(
        name="Pagination",
        description="Pagination of Responses: more information coming soon.",
        xSortOrder=500,
        xTraitTag=True,
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()


class SharedOpenAPIxTagGroups(Enum):
    ABOUT = OpenAPIxTagGroup(
        name="Information and Statistics",
        tags=[
            SharedOpenAPITags.DOCUMENTATION.value,
            SharedOpenAPITags.LOOKUP_SERVICES.value,
        ],
        xSortOrder=1,
    )
    SERVICES = OpenAPIxTagGroup(
        name="Services",
        tags=[
            SharedOpenAPITags.GENOME_BROWSER.value,
            SharedOpenAPITags.LOCUSZOOM.value,
            SharedOpenAPITags.LOOKUP_SERVICES.value,
        ],
        xSortOrder=90,
    )
    DATA_TRACKS = OpenAPIxTagGroup(
        name="Data Tracks",
        tags=[
            SharedOpenAPITags.TRACK_RECORD.value,
            SharedOpenAPITags.GWAS_TRACK_RECORD.value,
            SharedOpenAPITags.XQTL_TRACK_RECORD.value,
        ],
        xSortOrder=80,
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()

    @classmethod
    def list(cls) -> List[OpenAPIxTagGroup]:
        return [member.value for member in cls]
