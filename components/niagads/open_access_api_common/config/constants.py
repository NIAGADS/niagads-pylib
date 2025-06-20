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
        description="general information and overview statistics about the NIAGADS Open Access resources queried by this API.",
        xSortOrder=10,
        xDisplayName="Documentation",
    )
    TRACK_RECORD = OpenAPITag(
        name="Metadata",
        description="endpoints that retrieve track record metadata",
        xSortOrder=300,
        xDisplayName="Track Metadata",
    )
    TRACK_DATA = OpenAPITag(
        name="Track Data Retrieval",
        description="endpoints that retrieve track data",
        xTraitTag=False,
        xSortOrder=330,
    )
    XQTL_TRACK_RECORD = OpenAPITag(
        name="QTL",
        description="endpoints that retrieve xQTL track data or metadata",
        xSortOrder=312,
        xDisplayName="xQTLs",
    )
    GWAS_TRACK_RECORD = OpenAPITag(
        name="SumStats",
        description="endpoints that retrieve GWAS summary statistics track data or metadata",
        xSortOrder=310,
        xDisplayName="GWAS Summary Statistics",
    )
    GENE_RECORD = OpenAPITag(
        name="Gene",
        description="endpoints that retrieve gene-specific annotations",
        xSortOrder=200,
        xDisplayName="Genes",
    )
    VARIANT_RECORD = OpenAPITag(
        name="Variant",
        description="endpoints that retrieve variant-specific annotations",
        xSortOrder=100,
        xDisplayName="Variants",
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
        xSortOrder=400,
        xDisplayName="Genome Browser",
    )
    LOCUSZOOM = OpenAPITag(
        name="LocusZoom",
        description="service endpoints generating for NIAGADS LocusZoom data adapters",
        xSortOrder=420,
    )
    LOOKUP_SERVICES = OpenAPITag(
        name="Lookups",
        description="service endpoints that provide quick record lookups based on relational data (e.g., feature location)",
        xSortOrder=510,
        xDisplayName="Lookup Services",
    )
    RECORD_SEARCH = OpenAPITag(
        name="Search",
        description="service endpoints that find feature, track, or data records based by metadata or annotation text search",
        xSortOrder=500,
        xDisplayName="Record Search",
    )
    ONTOLOGIES = OpenAPITag(
        name="Ontologies",
        description="data descriptors, including allowable values for search filter fields",
        xSortOrder=530,
        xDisplayName="Data Dictionary",
    )
    PAGINATION = OpenAPITag(
        name="Pagination",
        description="Pagination of Responses: more information coming soon.",
        xSortOrder=1000,
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
            SharedOpenAPITags.ONTOLOGIES.value,
            SharedOpenAPITags.COLLECTIONS.value,
        ],
        xSortOrder=20,
    )
    SEARCH = OpenAPIxTagGroup(
        name="Search",
        tags=[
            SharedOpenAPITags.RECORD_SEARCH.value,
            SharedOpenAPITags.LOOKUP_SERVICES.value,
        ],
        xSortOrder=85,
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
            SharedOpenAPITags.TRACK_DATA.value,
            SharedOpenAPITags.GWAS_TRACK_RECORD.value,
            SharedOpenAPITags.XQTL_TRACK_RECORD.value,
            SharedOpenAPITags.COLLECTIONS.value,
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
