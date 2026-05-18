from typing import List, Union
from niagads.api.common.models.domain.entities.variant import (
    AnnotatedVariant,
    Variant,
    VariantAnnotation,
    VariantDescriptor,
)
from niagads.api.common.models.response.base import BaseResponseModel


class VariantResponse(BaseResponseModel):
    data: List[Union[VariantDescriptor, Variant, AnnotatedVariant]]


class VariantAnnotation(BaseResponseModel):
    data: List[VariantAnnotation]
