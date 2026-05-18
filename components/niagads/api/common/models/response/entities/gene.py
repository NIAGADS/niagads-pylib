from typing import List, Union
from niagads.api.common.models.domain.entities.gene import (
    AnnotatedGene,
    Gene,
    GeneAnnotation,
    GeneDescriptor,
)
from niagads.api.common.models.response.base import BaseResponseModel


class GeneResponse(BaseResponseModel):
    data: List[Union[GeneDescriptor, Gene, AnnotatedGene]]


class GeneAnnotationResponse(BaseResponseModel):
    data: List[GeneAnnotation]
