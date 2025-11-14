# http client
from enum import Enum

from niagads.api.common.app.openapi import OpenAPITag

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
    STATUS = OpenAPITag(
        name="Status",
        description="general information and statistics about the NIAGADS Open Access resources queried by this API.",
        x_display_name="Status",
        x_sort_order=1,
    )
    ENTITY_LOOKUP = OpenAPITag(
        name="Lookup",
        description="retrieve entity nomenclature, metadata, or annotations by ID",
        x_sort_order=10,
        x_display_name="Entity Lookup",
    )
    SEARCH = OpenAPITag(
        name="Search",
        description="find entities matching search criteria",
        x_sort_order=20,
        x_display_name="Entity Search",
    )
    DATA = OpenAPITag(
        name="Data",
        description="Retrieve data or annotations matching search criteria",
        x_sort_order=30,
        x_display_name="Search and Data Retrieval",
    )
    SERVICE = OpenAPITag(
        name="Service",
        description="retrieve data formatted for input to NIAGADS visualization tools or services",
        x_sort_order=40,
        x_display_name="GWAS Summary Statistics",
    )
    DICTIONARY = OpenAPITag(
        name="Dictionary",
        description="search or retrieve controlled vocabularies and ontologies",
        x_sort_order=50,
    )

    def __str__(self):
        return self.value.name

    def serialize(self):
        return self.value.model_dump()

    @classmethod
    def list(cls):
        return [tag.value for tag in cls]
