"""Supported ASK operations and their existing API response configurations."""

from niagads.api.common.models.annotations.associations import (
    VariantAssociation,
)
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.gene.records import Gene
from niagads.api.common.models.entities.track.records import TrackMetadata
from niagads.api.common.models.entities.variant.records import Variant
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.types import AnnotationKind
from niagads.common.models.base import CustomBaseModel
from niagads.common.search.models.record import SearchMatch
from niagads.common.types import Entity
from pydantic import ConfigDict


class AskOperation(CustomBaseModel):
    """Describe a supported endpoint independently of its presentation."""

    model_config = ConfigDict(frozen=True)

    endpoint: str
    entity: Entity
    annotation: AnnotationKind | None
    response_config: ResponseConfiguration


OPERATIONS = {
    "search_tracks": AskOperation(
        endpoint="/query/tracks",
        entity=Entity.TRACK,
        annotation=None,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=SearchMatch
        ),
    ),
    "search_genes": AskOperation(
        endpoint="/query/genes",
        entity=Entity.GENE,
        annotation=None,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=SearchMatch
        ),
    ),
    "gene": AskOperation(
        endpoint="/record/gene/{gene}",
        entity=Entity.GENE,
        annotation=AnnotationKind.REPORT,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=Gene
        ),
    ),
    "variant": AskOperation(
        endpoint="/record/variant/{variant}",
        entity=Entity.VARIANT,
        annotation=AnnotationKind.REPORT,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=Variant
        ),
    ),
    "track": AskOperation(
        endpoint="/record/track/{track}",
        entity=Entity.TRACK,
        annotation=AnnotationKind.REPORT,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=TrackMetadata
        ),
    ),
    "gene_structure": AskOperation(
        endpoint="/record/gene/{gene}/structure",
        entity=Entity.GENE,
        annotation=AnnotationKind.STRUCTURE,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=DynamicRecord
        ),
    ),
    "gene_associations": AskOperation(
        endpoint="/record/gene/{gene}/associations",
        entity=Entity.GENE,
        annotation=AnnotationKind.ASSOCIATIONS,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=VariantAssociation
        ),
    ),
    "variant_associations": AskOperation(
        endpoint="/record/variant/{variant}/associations",
        entity=Entity.VARIANT,
        annotation=AnnotationKind.ASSOCIATIONS,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=VariantAssociation
        ),
    ),
    "region_associations": AskOperation(
        endpoint="/record/region/associations",
        entity=Entity.REGION,
        annotation=AnnotationKind.ASSOCIATIONS,
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=VariantAssociation
        ),
    ),
}

SEARCH_OPERATIONS = {
    operation.entity: name
    for name, operation in OPERATIONS.items()
    if operation.response_config.record_model is SearchMatch
}
