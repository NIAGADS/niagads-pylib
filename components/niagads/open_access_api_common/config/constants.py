# http client
from enum import Enum

from niagads.open_access_api_common.types import OpenAPITag, OpenAPIxGroupTag


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
        description="general information about the knowledge base, including lookups for data descriptors",
    )
    TRACK_RECORD = OpenAPITag(
        name="Track Records",
        description="endpoints that retrieve track metadata",
    )
    GENE_RECORD = OpenAPITag(
        name="Gene Records",
        description="endpoints that retrieve gene-specific annotations",
    )
    VARIANT_RECORD = OpenAPITag(
        name="Variant Records",
        description="endpoints that retrieve variant-specific annotations",
    )
    TRACK_DATA = OpenAPITag(
        name="Track Data Retrieval",
        description="endpoints that retrieve track data",
    )
    COLLECTIONS = OpenAPITag(
        name="Collections",
        description="endpoints that retrieve curated lists of records",
    )
    RECORD_BY_ID = OpenAPITag(
        name="Record(s) by ID",
        description="find gene, variant, or data track records by ID",
    )
    RECORD_BY_REGION = OpenAPITag(
        name="Record(s) by Region",
        description="find gene, variant, or data track records by Genomic Region",
    )
    RECORD_BY_TEXT = OpenAPITag(
        name="Record(s) by Text Search",
        description="find gene, variant, or data track records by metadata text search",
    )
    SERVICES = OpenAPITag(
        name="Services",
        description="service endpoints that do specific lookups or return JSON responses for downstream tools, such as the Genome Browser",
    )
    GENOME_BROWSER = OpenAPITag(
        name="Genome Browser",
        description="service endpoints generating configuration files and data responses for NIAGADS Genome Browser Tracks",
    )
    LOCUSZOOM = OpenAPITag(
        name="LocusZoom",
        description="service endpoints generating for NIAGADS LocusZoom data adapters",
    )
    SPECIFICATION = OpenAPITag(
        name="OpenAPI Specification",
        description="service endpoints that retrieve the OpenAPI specification",
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()


class SharedOpenAPIxGroupTags(Enum):
    ABOUT = OpenAPIxGroupTag(name="About", tags=[str(SharedOpenAPITags.ABOUT)])
    SERVICES = OpenAPIxGroupTag(
        name="Services",
        tags=[
            str(SharedOpenAPITags.SERVICES),
            str(SharedOpenAPITags.GENOME_BROWSER),
            str(SharedOpenAPITags.LOCUSZOOM),
            str(SharedOpenAPITags.SPECIFICATION),
        ],
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()
