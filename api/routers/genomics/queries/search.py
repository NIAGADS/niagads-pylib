from enum import auto
from typing import List

from api.common.enums.base_enums import EnumParameter
from api.models.response_model_properties import QueryDefinition
from api.models.search import RecordSearchResult



class SearchType(EnumParameter): # TODO: move to parameters
    GENE = auto()
    VARIANT = auto()
    FEATURE = auto()
    TRACK = auto()
    GLOBAL = auto()
    
    @classmethod
    def get_description(cls, inclValues=True):
        message = 'Type of site search to perform.'    
        return message + f' {super().get_description()}' if inclValues else message

# these are all fetchOne b/c the result is aggregated into a JSON object
# TODO: test if SqlAlchemy can return JSON directly instead of returning the JSON as text and then parsing back

class SiteSearchQueryDefinition(QueryDefinition):
    searchType: SearchType
    resultType: List[RecordSearchResult]   
    fetchOne: bool = True
    
    def __get_cte(self):
        
        geneSql = "SELECT * FROM gene_text_search((SELECT :keyword FROM st))"
        variantSql = "SELECT * FROM variant_text_search((SELECT :keyword FROM st))"
        trackSql = "SELECT * FROM gwas_dataset_text_search((SELECT :keyword FROM st))"
        
        match self.searchType:
            case SearchType.GENE:
                return geneSql
            case SearchType.VARIANT:
                return variantSql
            case SearchType.TRACK:
                return trackSql
            case SearchType.FEATURE:
                return ('WITH Matches AS ({geneSql}'
                    f' UNION {variantSql}'
                    f' ORDER BY match_rank, record_type, display ASC)'
                )
            case _:
                return (f'WITH Matches AS ({geneSql}'
                    f' UNION {variantSql} UNION {trackSql}'
                    f' ORDER BY match_rank, record_type, display ASC)'
                )

    
    def model_post_init(self, __context):        
        match self.searchType:
            case SearchType.FEATURE:
                self.bindParameters = ['keyword', 'keyword']
            case SearchType.GLOBAL:
                self.bindParameters = ['keyword', 'keyword', 'keyword']
            case _:
                self.bindParameters = ['keyword']
        
        self.name = f'{self.searchType.value}-text-search'
        self.query = f'SELECT jsonb_agg(*)::text AS result FROM ({self.__get_cte()}) m'