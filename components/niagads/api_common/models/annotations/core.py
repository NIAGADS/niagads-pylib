from niagads.api_common.models.features.variant import (
    VariantDisplayAnnotation,
    VariantFeature,
)


class AnnotatedVariantFeature(VariantFeature, VariantDisplayAnnotation):
    # for association tables
    pass
