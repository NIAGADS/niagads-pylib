from enum import auto
from typing import List

from niagads.enums.core import EnumParameter
from niagads.open_access_api_common.models.services.query import QueryDefinition


class SearchType(EnumParameter):  # TODO: move to parameters
    GENE = auto()
    VARIANT = auto()
    FEATURE = auto()
    TRACK = auto()
    GLOBAL = auto()

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Type of site search to perform."
        return message + f" {super().get_description()}" if inclValues else message


# these are all fetchOne b/c the result is aggregated into a JSON object
# TODO: test if SqlAlchemy can return JSON directly instead of returning the JSON as text and then parsing back


class SiteSearchQuery(QueryDefinition):
    searchType: SearchType
    fetchOne: bool = False
    query: str = ""  # gets assigned dynamically by model_post_init
    bindParameters: List[str] = ["keyword"]

    def __get_CTE(self):
        geneSql = "SELECT * FROM gene_text_search((SELECT st.keyword FROM st))"
        variantSql = "SELECT * FROM variant_text_search((SELECT st.keyword FROM st))"
        trackSql = "SELECT * FROM gwas_dataset_text_search((SELECT st.keyword FROM st))"

        match self.searchType:
            case SearchType.GENE:
                return geneSql
            case SearchType.VARIANT:
                return variantSql
            case SearchType.TRACK:
                return trackSql
            case SearchType.FEATURE:
                return f"{geneSql} UNION ALL {variantSql}"
            case _:
                return f"{geneSql} UNION ALL {variantSql} UNION ALL {trackSql}"

    def model_post_init(self, __context):
        match self.searchType:
            case SearchType.FEATURE:
                self.bindParameters = ["keyword"] * 2
            case SearchType.GLOBAL:
                self.bindParameters = ["keyword"] * 3
            case _:
                self.bindParameters = ["keyword"]

        self.query = (
            f"WITH st AS (SELECT trim(:keyword)::text AS keyword)"
            f" {self.__get_CTE()}"
            f" ORDER BY match_rank, record_type, display ASC"
        )


""" e.g. usage:
query = SiteSearchQuery(
    searchType = SearchType.GENE
)
"""
