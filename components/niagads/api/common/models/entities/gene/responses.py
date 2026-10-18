from typing import List, Union

from niagads.api.common.models.entities.gene.records import (
    Gene,
    GeneBrief,
    GeneDescriptor,
)
from niagads.api.common.models.responses.data import DataResponse


class GeneResponse(DataResponse):
    _xml_root = "genes"
    data: List[Union[GeneDescriptor, GeneBrief, Gene]]
