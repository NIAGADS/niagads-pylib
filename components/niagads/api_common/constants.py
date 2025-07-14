# http client
from enum import Enum
from typing import List

from niagads.api_common.app.openapi import OpenAPITag, OpenAPIxTagGroup

HTTP_CLIENT_TIMEOUT = 30  # timeout in seconds

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 100

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
        description="general information and overesponse_view statistics about the NIAGADS Open Access resources queried by this API.",
        x_sort_order=10,
        x_display_name="Documentation",
    )
    TRACK_RECORD = OpenAPITag(
        name="Metadata",
        description="endpoints that retrieve track record metadata",
        x_sort_order=300,
        x_display_name="Track Metadata",
    )
    TRACK_DATA = OpenAPITag(
        name="Track Data Retrieval",
        description="endpoints that retrieve track data",
        x_sort_order=330,
    )
    XQTL_TRACK_RECORD = OpenAPITag(
        name="QTL",
        description="endpoints that retrieve xQTL track data or metadata",
        x_sort_order=312,
        x_display_name="xQTLs",
    )
    GWAS_TRACK_RECORD = OpenAPITag(
        name="SumStats",
        description="endpoints that retrieve GWAS summary statistics track data or metadata",
        x_sort_order=310,
        x_display_name="GWAS Summary Statistics",
    )
    GENE_RECORD = OpenAPITag(
        name="Gene",
        description="endpoints that retrieve gene-specific annotations",
        x_sort_order=200,
        x_display_name="Genes",
    )
    VARIANT_RECORD = OpenAPITag(
        name="Variant",
        description="endpoints that retrieve variant-specific annotations",
        x_sort_order=100,
        x_display_name="Variants",
    )

    COLLECTIONS = OpenAPITag(
        name="Collection",
        description="endpoints that retrieve curated lists of records",
        x_sort_order=19,
        x_display_name="Collections",
    )
    GENOME_BROWSER = OpenAPITag(
        name="Browser",
        description="service endpoints generating configuration files, data adapters, and search services for NIAGADS Genome Browser Tracks",
        x_sort_order=400,
        x_display_name="Genome Browser",
    )
    LOCUSZOOM = OpenAPITag(
        name="LocusZoom",
        description="service endpoints generating for NIAGADS LocusZoom data adapters",
        x_sort_order=420,
    )
    LOOKUP_SERVICES = OpenAPITag(
        name="Lookups",
        description="service endpoints that provide quick record lookups based on relational data (e.g., feature location)",
        x_sort_order=510,
        x_display_name="Lookup Services",
    )
    RECORD_SEARCH = OpenAPITag(
        name="Search",
        description="service endpoints that find feature, track, or data records based by metadata or annotation text search",
        x_sort_order=500,
        x_display_name="Record Search",
    )
    ONTOLOGIES = OpenAPITag(
        name="Ontologies",
        description="data descriptors, including allowable values for search filter fields",
        x_sort_order=530,
        x_display_name="Data Dictionary",
    )
    PAGINATION = OpenAPITag(
        name="Pagination",
        description="Pagination of Responses: more information coming soon.",
        x_sort_order=1000,
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
            SharedOpenAPITags.ONTOLOGIES.value,
            SharedOpenAPITags.COLLECTIONS.value,
        ],
        x_sort_order=20,
    )
    SEARCH = OpenAPIxTagGroup(
        name="Search",
        tags=[
            SharedOpenAPITags.RECORD_SEARCH.value,
            SharedOpenAPITags.LOOKUP_SERVICES.value,
        ],
        x_sort_order=85,
    )
    SERVICES = OpenAPIxTagGroup(
        name="Services",
        tags=[
            SharedOpenAPITags.GENOME_BROWSER.value,
            SharedOpenAPITags.LOCUSZOOM.value,
            SharedOpenAPITags.LOOKUP_SERVICES.value,
        ],
        x_sort_order=90,
    )
    DATA_TRACKS = OpenAPIxTagGroup(
        name="Data Tracks",
        tags=[
            SharedOpenAPITags.TRACK_RECORD.value,
            SharedOpenAPITags.TRACK_DATA.value,
            SharedOpenAPITags.GWAS_TRACK_RECORD.value,
            SharedOpenAPITags.XQTL_TRACK_RECORD.value,
            SharedOpenAPITags.COLLECTIONS.value,
        ],
        x_sort_order=80,
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()

    @classmethod
    def list(cls) -> List[OpenAPIxTagGroup]:
        return [member.value for member in cls]
