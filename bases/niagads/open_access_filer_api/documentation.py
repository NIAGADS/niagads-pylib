"""OpenAPI and related metadata for the Open Access FILER microservice."""

from typing import Set

from niagads.open_access_api_common.app import OpenAPITag
from niagads.open_access_api_common.types import T_PubMedID

OPEN_API_TAGS: OpenAPITag = {
    "name": "FILER Functional Genomics Repository",
    "description": (
        f"Query tracks and track data in FILER, "
        f"a functional genomics database developed by NIAGADS "
        f"with the most comprehensive harmonized, extensible, "
        f"indexed, searchable human functional genomics data collection "
        f"across >20 data sources."
    ),
    "externalDocs": {
        "description": "FILER Website",
        "url": "https://tf.lisanwanglab.org/FILER/",
    },
}

PUBMED_IDS: Set[T_PubMedID] = ["PMID:35047815"]

ROUTE_NAME: str = OPEN_API_TAGS["name"]
