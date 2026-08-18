from typing import List, Union

from niagads.api.common.models.entities.variants.records import (
    AnnotatedVariant,
    Variant,
    VariantAnnotation,
    VariantDescriptor,
)
from niagads.api.common.models.response.base import DataResponse


class VariantResponse(DataResponse):
    data: List[Union[VariantDescriptor, Variant, AnnotatedVariant]]


class VariantAnnotation(DataResponse):
    data: List[VariantAnnotation]
