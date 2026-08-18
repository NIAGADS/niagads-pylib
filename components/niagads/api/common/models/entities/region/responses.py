from typing import List

from niagads.api.common.models.entities.region.features.bed import BEDFeature
from niagads.api.common.models.responses.data import DataResponse


class BEDResponse(DataResponse):
    data: List[BEDFeature]
