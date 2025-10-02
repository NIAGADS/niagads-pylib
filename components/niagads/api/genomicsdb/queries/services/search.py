from enum import auto
from typing import List

from niagads.api.common.models.services.query import QueryDefinition
from niagads.api.common.parameters.enums import EnumParameter


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
    search_type: SearchType
    fetch_one: bool = False
    query: str = ""  # gets assigned dynamically by model_post_init
    bind_parameters: List[str] = ["keyword"]

    def __get_CTE(self):
        gene_sql = "SELECT * FROM gene_text_search((SELECT st.keyword FROM st))"
        variant_sql = "SELECT * FROM variant_text_search((SELECT st.keyword FROM st))"
        track_sql = (
            "SELECT * FROM gwas_dataset_text_search((SELECT st.keyword FROM st))"
        )

        match self.search_type:
            case SearchType.GENE:
                return gene_sql
            case SearchType.VARIANT:
                return variant_sql
            case SearchType.TRACK:
                return track_sql
            case SearchType.FEATURE:
                return f"{gene_sql} UNION ALL {variant_sql}"
            case _:
                return f"{gene_sql} UNION ALL {variant_sql} UNION ALL {track_sql}"

    def model_post_init(self, __context):
        match self.search_type:
            case SearchType.FEATURE:
                self.bind_parameters = ["keyword"] * 2
            case SearchType.GLOBAL:
                self.bind_parameters = ["keyword"] * 3
            case _:
                self.bind_parameters = ["keyword"]

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
