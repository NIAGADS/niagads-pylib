from typing import List
from api.models.base_models import QueryDefinition
from api.models.search import RecordSearchResult

__GENE_TEXT_SEARCH_SQL="SELECT * FROM gene_text_search((SELECT :keyword FROM st))"
__VARIANT_TEXT_SEARCH_SQL="SELECT * FROM variant_text_search((SELECT :keyword FROM st))"
__TRACK_TEXT_SEARCH_SQL="SELECT * FROM gwas_dataset_text_search((SELECT :keyword FROM st))"

__GLOBAL_SEARCH_CTE=(f'WITH Matches AS ({__GENE_TEXT_SEARCH_SQL}'
    f' UNION {__VARIANT_TEXT_SEARCH_SQL} UNION {__TRACK_TEXT_SEARCH_SQL}'
    f' ORDER BY match_rank, record_type, display ASC)'
)

__FEATURE_SEARCH_CTE=('WITH Matches AS ({__GENE_TEXT_SEARCH_SQL}'
    f' UNION {__VARIANT_TEXT_SEARCH_SQL}'
    f' ORDER BY match_rank, record_type, display ASC)'
)



# these are all fetchOne b/c the result is aggregated into a JSON object
# TODO: test if SqlAlchemy can return JSON directly instead of returning the JSON as text and then parsing back

GENE = QueryDefinition(
    name='gene-text-search',
    query="SELECT jsonb_agg(*)::text AS result FROM (" + __GENE_TEXT_SEARCH_SQL + ") m",
    resultType=List[RecordSearchResult],
    bindParameters=['keyword'],
    fetchOne=True
)

VARIANT = QueryDefinition(
    name='variant-text-search',
    query="SELECT jsonb_agg(*)::text AS result FROM (" + __VARIANT_TEXT_SEARCH_SQL + ") m",
    resultType=List[RecordSearchResult],
    bindParameters=['keyword'],
    fetchOne=True
)

TRACK = QueryDefinition(
    name='variant-text-search',
    query="SELECT jsonb_agg(*)::text AS result FROM (" + __TRACK_TEXT_SEARCH_SQL + ") m",
    resultType=List[RecordSearchResult],
    bindParameters=['keyword'],
    fetchOne=True
)

GLOBAL = QueryDefinition(
    name='global-text-search',
    query=f'{__GLOBAL_SEARCH_CTE} SELECT jsonb_agg(matches)::text AS result FROM Matches',
    resultType=List[RecordSearchResult],
    bindParameters=['keyword', 'keyword', 'keyword'],
    fetchOne=True
)

FEATURE = QueryDefinition(
    name='global-text-search',
    query=f'{__FEATURE_SEARCH_CTE} SELECT jsonb_agg(matches)::text AS result FROM Matches',
    resultType=List[RecordSearchResult],
    bindParameters=['keyword', 'keyword'],
    fetchOne=True
)