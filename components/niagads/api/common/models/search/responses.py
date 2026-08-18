from typing import List

from niagads.api.common.models.responses.data import DataResponse
from niagads.api.common.models.search.records import SearchResult


class EntityMatchResponse(DataResponse):
    data: List[SearchResult]

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )
