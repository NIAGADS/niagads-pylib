from typing import List

from components.niagads.common.search.models.record import LookupMatch
from niagads.api.common.models.responses.data import DataResponse


class EntityMatchResponse(DataResponse):
    data: List[LookupMatch]

    def to_delimited_text(self, *, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )
