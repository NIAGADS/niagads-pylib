from typing import List
from niagads.api.common.models.domain.entities.features.bed import BEDFeature
from niagads.api.common.models.response.base import BaseResponseModel


class BEDResponse(BaseResponseModel):
    data: List[BEDFeature]
