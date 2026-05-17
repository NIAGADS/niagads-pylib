from typing import List
from niagads.api.common.data_models.response.record import RecordResponse
from niagads.api.common.data_models.search import EntityRecordMatch


class RecordSearchResultResponse(RecordResponse):
    data: List[EntityRecordMatch]

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )
