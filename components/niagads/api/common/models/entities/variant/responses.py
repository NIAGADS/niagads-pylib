from typing import List, Union

from niagads.api.common.models.entities.variant.records import (
    Variant,
    Variant,
    VariantDescriptor,
)
from niagads.api.common.models.responses.data import DataResponse


class VariantResponse(DataResponse):
    data: List[Union[VariantDescriptor, Variant, Variant]]


# TODO: come back to this
# class ColocatedVariants(CustomBaseModel):
#    alternative_alleles: Optional[List[str]] = None
#    colocated_variants: Optional[List[str]] = None

"""
class VariantAnnotationResponse(DataResponse):
    data: Union[
        List[ColocatedVariants],
        List[VariantFunction],
        List[AlleleFrequencies],
        List[CustomBaseModel],
    ]

"""
