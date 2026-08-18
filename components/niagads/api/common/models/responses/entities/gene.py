from typing import List, Union

from niagads.api.common.models.entities.genes.gene import (
    AnnotatedGene,
    Gene,
    GeneAnnotation,
    GeneDescriptor,
)
from niagads.api.common.models.response.base import DataResponse


class GeneResponse(DataResponse):
    data: List[Union[GeneDescriptor, Gene, AnnotatedGene]]


class GeneAnnotationResponse(DataResponse):
    data: List[GeneAnnotation]
