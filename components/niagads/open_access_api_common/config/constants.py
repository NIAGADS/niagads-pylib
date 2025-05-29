# http client
from enum import Enum
from typing import List

from niagads.open_access_api_common.types import OpenAPITag, OpenAPIxTagGroup


HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 10

# Responses
RESPONSES = {
    404: {"description": "Item not found"},
    422: {"description": "Validation Error"},
    500: {"description": "Internal Server Error"},
    501: {"description": "Not Implemented"},
    429: {"description": "Too many requests"},
}

# regular expressions
SHARD_PATTERN = r"chr(\d{1,2}|[XYM]|MT)"

# default values
DEFAULT_NULL_STRING = "NA"


class SharedOpenAPITags(Enum):
    ABOUT = OpenAPITag(
        name="Resource Information",
        description="general information and over statistics about the NIAGADS Open Access resources queried by this API, including lookups for data descriptors",
        xSortOrder=10,
    )
    TRACK_RECORD = OpenAPITag(
        name="Track Metadata",
        description="endpoints that retrieve track metadata",
        xSortOrder=20,
    )
    XQTL_TRACK_RECORD = OpenAPITag(
        name="xQTLs",
        description="endpoints that retrieve xQTL track data or metadata",
        xSortOrder=21,
    )
    GWAS_TRACK_RECORD = OpenAPITag(
        name="GWAS Summary Statistics",
        description="endpoints that retrieve GWAS summary statistics track data or metadata",
        xSortOrder=22,
    )
    GENE_RECORD = OpenAPITag(
        name="Genes",
        description="endpoints that retrieve gene-specific annotations",
        xSortOrder=11,
    )
    VARIANT_RECORD = OpenAPITag(
        name="Variants",
        description="endpoints that retrieve variant-specific annotations",
        xSortOrder=12,
    )
    TRACK_DATA = OpenAPITag(
        name="Data Retrieval",
        description="endpoints that retrieve track data",
        xTraitTag=True,
        xSortOrder=13,
    )
    COLLECTIONS = OpenAPITag(
        name="Collections",
        description="endpoints that retrieve curated lists of records",
        xSortOrder=19,
    )
    RECORD_BY_ID = OpenAPITag(
        name="Record(s) by ID",
        description="find gene, variant, or data track records by ID",
        xTraitTag=True,
        xSortOrder=30,
    )
    RECORD_BY_REGION = OpenAPITag(
        name="Record(s) by Region",
        description="find gene, variant, or data track records by Genomic Region",
        xTraitTag=True,
        xSortOrder=31,
    )
    RECORD_BY_TEXT = OpenAPITag(
        name="Record(s) by Text Search",
        description="find gene, variant, or data track records by metadata text search",
        xTraitTag=True,
        xSortOrder=32,
    )
    SERVICES = OpenAPITag(
        name="All Services",
        description="service endpoints that do specific lookups or return JSON responses for downstream tools, such as the Genome Browser",
        xTraitTag=True,
        xSortOrder=40,
    )
    GENOME_BROWSER = OpenAPITag(
        name="Genome Browser",
        description="service endpoints generating configuration files, data adapters, and search services for NIAGADS Genome Browser Tracks",
        xSortOrder=41,
    )
    LOCUSZOOM = OpenAPITag(
        name="LocusZoom",
        description="service endpoints generating for NIAGADS LocusZoom data adapters",
        xSortOrder=42,
    )
    LOOKUP_SERVICES = OpenAPITag(
        name="Lookup Services",
        description="service endpoints that provide quick record lookups based on relational data (e.g., root shard for sharded data track)",
        xSortOrder=43,
    )
    SPECIFICATION = OpenAPITag(
        name="OpenAPI Specification",
        description="service endpoints that retrieve the OpenAPI specification",
        xSortOrder=100,
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()


class SharedOpenAPIxTagGroups(Enum):
    ABOUT = OpenAPIxTagGroup(
        name="Information and Statistics",
        tags=[SharedOpenAPITags.ABOUT.value, SharedOpenAPITags.SPECIFICATION.value],
        xSortOrder=1,
    )
    SERVICES = OpenAPIxTagGroup(
        name="Services",
        tags=[
            SharedOpenAPITags.SERVICES.value,
            SharedOpenAPITags.GENOME_BROWSER.value,
            SharedOpenAPITags.LOCUSZOOM.value,
            SharedOpenAPITags.LOOKUP_SERVICES.value,
        ],
        xSortOrder=90,
    )
    DATA_TRACKS = OpenAPIxTagGroup(
        name="Data Tracks",
        tags=[
            SharedOpenAPITags.TRACK_DATA.value,
            SharedOpenAPITags.TRACK_RECORD.value,
            SharedOpenAPITags.GWAS_TRACK_RECORD.value,
            SharedOpenAPITags.XQTL_TRACK_RECORD.value,
        ],
        xSortOrder=20,
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()

    @classmethod
    def list(cls) -> List[OpenAPIxTagGroup]:
        return [member.value for member in cls]
