from typing import List, Union
from niagads.api.common.models.domain.entities.variant import (
    AnnotatedVariant,
    Variant,
    VariantAnnotation,
    VariantDescriptor,
)
from niagads.api.common.models.response.base import StandardDataSerializationResponse


class VariantResponse(StandardDataSerializationResponse):
    data: List[Union[VariantDescriptor, Variant, AnnotatedVariant]]


class VariantAnnotation(StandardDataSerializationResponse):
    data: List[VariantAnnotation]
