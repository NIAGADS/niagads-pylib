from typing import List

from niagads.api.common.models.response.base import BaseResponseModel
from niagads.api.common.models.domain.entities.entity import EntityRecordMatch


class EntityMatchResponse(BaseResponseModel):
    data: List[EntityRecordMatch]

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )
