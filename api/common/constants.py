from typing import Any, Dict, List, Union

DEFAULT_NULL_STRING='NA'

JSON_TYPE = Union[Dict[str, Any], List[Any], int, float, str, bool, None]

ALLOWABLE_FILER_TRACK_FILTERS = {
    "dataSource": "original data source ", 
    "assay": "assay type", 
    "featureType": "feature type", 
    "antibodyTarget": "target of ChIP-seq or other immunoprecipitation assay",
    "project": "member of a collection of related tracks, often an ENCODE project",
    "tissue": "tissue associated with biosample"
}

BIOSAMPLE_FIELDS = ["life_stage", "biosample_term", "system_category",
    "tissue_category", "biosample_display",
    "biosample_summary", "biosample_term_id"]

TRACK_SEARCH_FILTER_FIELD_MAP = { 
    'biosample': {
        'model_field' : 'biosample_characteristics', 
        'description': "searches across biosample characteristics, including, " +
            "but not limited to: biological system, tissue, cell type, cell line, " +
            "life stage; can be searched using ontology terms from UBERON (tissues), CL (cells), " + 
            "CLO (cell lines), and EFO (experimental factors); NOTE: biosample term matches are fuzzy and case insensitive"
        },
    'antibody': {
        'model_field': 'antibody_target',
        'description': "the antibody target, e.g. in a CHiP-SEQ experiment; " + 
            "we recommend searching for gene targets with `like` operator as many are prefixed"
    },
    'assay': {
        'model_field': 'assay',
        'description': 'type of assay'
    },
    'feature': {
        'model_field': 'feature_type',
        'description': "the type of functional genomics feature reported in the data track"
    },
    'analysis': {
        'model_field': 'analysis',
        'description': "type of statistical analysis, if relevant"
    },
    'classification': {
        'model_field': 'classification',
        'description': "specific categorization or classification of the data reported in the data track"
    },
    'category': {
        'model_field': 'data_category',
        'description': "broad categorization of the type of the data reported in the data track"
    },
    'datasource': {
        'model_field': 'data_source',
        'description': "original third-party data source for the track"
    },
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

# regular expressions
SHARD_PATTERN = r'chr(\d{1,2}|[XYM]|MT)'