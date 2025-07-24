from niagads.api_common.models.core import RowModel
from niagads.api_common.models.features.genomic import GenomicRegion
from niagads.api_common.models.features.variant import (
    VariantDisplayAnnotation,
    VariantFeature,
)
from pydantic import Field


class AnnotatedVariantFeature(VariantFeature, VariantDisplayAnnotation):
    # for association tables
    pass
