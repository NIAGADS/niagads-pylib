from typing import List

from niagads.api.common.models.domain.entities.entity import EntityRecordMatch
from niagads.api.common.models.response.base import DataResponse


class EntityMatchResponse(DataResponse):
    data: List[EntityRecordMatch]

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )
