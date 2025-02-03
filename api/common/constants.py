from typing import Any, Dict, List, Union

JSON_TYPE = Union[Dict[str, Any], List[Any], int, float, str, bool, None]

ALLOWABLE_FILER_TRACK_FILTERS = {
    "dataSource": "original data source ", 
    "assay": "assay type", 
    "featureType": "feature type", 
    "antibodyTarget": "target of ChIP-seq or other immunoprecipitation assay",
    "project": "member of a collection of related tracks, often an ENCODE project",
    "tissue": "tissue associated with biosample"
}

FILER_N_TRACK_LOOKUP_LIMIT = 50

# pagination
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 10

# http client 
HTTP_CLIENT_TIMEOUT=30 # timeout in seconds

# cache db
# int or float in seconds specifying maximum timeout for the operations to last. By default (aiocache) its 5. Use 0 or None if you want to disable it.
CACHEDB_TIMEOUT=5 

