from typing import List
from api.models.base_models import QueryDefinition
from api.models.global_search import RecordSearchResult

GENE_TEXT_SEARCH_SQL="SELECT * FROM gene_text_search((SELECT :term FROM st))"
VARIANT_TEXT_SEARCH_SQL="SELECT * FROM variant_text_search((SELECT :term FROM st))"
TRACK_TEXT_SEARCH_SQL="SELECT * FROM gwas_dataset_text_search((SELECT :term FROM st))"
GLOBAL_SEARCH_SQL=(f'WITH Matches AS ({GENE_TEXT_SEARCH_SQL}'
    f' UNION {VARIANT_TEXT_SEARCH_SQL} UNION {TRACK_TEXT_SEARCH_SQL}'
    f' ORDER BY match_rank, record_type, display ASC)'
    f' SELECT jsonb_agg(matches)::text AS result FROM Matches'
)

# these are all fetchOne b/c the result is aggregated into a JSON object
# TODO: test if SqlAlchemy can return JSON directly instead of returning the JSON as text and then parsing back

GENE = QueryDefinition(
    name='gene-text-search',
    query="SELECT jsonb_agg(*)::text AS result FROM (" + GENE_TEXT_SEARCH_SQL + ") m",
    resultType=List[RecordSearchResult],
    bindParameters=['term'],
    fetchOne=True
)

VARIANT = QueryDefinition(
    name='variant-text-search',
    query="SELECT jsonb_agg(*)::text AS result FROM (" + VARIANT_TEXT_SEARCH_SQL + ") m",
    resultType=List[RecordSearchResult],
    bindParameters=['term'],
    fetchOne=True
)

TRACK = QueryDefinition(
    name='variant-text-search',
    query="SELECT jsonb_agg(*)::text AS result FROM (" + TRACK_TEXT_SEARCH_SQL + ") m",
    resultType=List[RecordSearchResult],
    bindParameters=['term'],
    fetchOne=True
)

GLOBAL = QueryDefinition(
    name='global-text-search',
    query=GLOBAL_SEARCH_SQL,
    resultType=List[RecordSearchResult],
    bindParameters=['term', 'term', 'term'],
    fetchOne=True
)