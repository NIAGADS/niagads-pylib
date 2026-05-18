from typing import List, Union
from niagads.api.common.models.domain.entities.gene import (
    AnnotatedGene,
    Gene,
    GeneAnnotation,
    GeneDescriptor,
)
from niagads.api.common.models.response.base import StandardDataSerializationResponse


class GeneResponse(StandardDataSerializationResponse):
    data: List[Union[GeneDescriptor, Gene, AnnotatedGene]]


class GeneAnnotationResponse(StandardDataSerializationResponse):
    data: List[GeneAnnotation]
