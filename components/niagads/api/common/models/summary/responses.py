from typing import List

from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.models.summary.records import APISummary


class APISummaryResponse(BaseResponseModel):
    data: APISummary

    def to_delimited_text(self, *, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "delimited text output not available for a API summary response."
        )
