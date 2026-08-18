from typing import List, Union

from niagads.api.common.models.entities.gene.records import (
    AnnotatedGene,
    Gene,
    GeneAnnotation,
    GeneDescriptor,
)
from niagads.api.common.models.responses.data import DataResponse


class GeneResponse(DataResponse):
    data: List[Union[GeneDescriptor, Gene, AnnotatedGene]]


class GeneAnnotationResponse(DataResponse):
    data: List[GeneAnnotation]
