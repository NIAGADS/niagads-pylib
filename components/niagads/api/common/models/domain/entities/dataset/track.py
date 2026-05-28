from typing import List, Optional, Union

from niagads.api.common.models.domain.base import CountRecordModel, ORMCompatibleRecord
from niagads.api.common.models.domain.mixins import (
    ORMCompatabileMixin,
    ResultMetricsMixin,
)
from niagads.common.genomic.features.models import GenomicFeatureType
from niagads.common.models.base import CustomBaseModel, SerializationOptions
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.track.models import TrackRecord
from niagads.common.track.models.samples import BiosampleCharacteristics
from niagads.genome_reference.human import GenomeBuild
from pydantic import ConfigDict, Field, field_serializer, model_validator


class BiosampleCharacteristicsReport(BiosampleCharacteristics):
    biosample_type: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Biosample: Type",
        description="the biological source of a sample used in an experiment",
    )


class TrackMetadataBrief(ORMCompatibleRecord):
    model_config = ConfigDict(is_summary=True)

    id: str = Field(title="Track ID", description="stable track identifier")
    name: str = Field(title="Name")
    description: Optional[str] = Field(default=None, title="Description")
    genome_build: GenomeBuild = Field(
        default=GenomeBuild.GRCh38,
        title="Genome Build",
        description=f"reference genome build",
    )
    feature_type: Optional[GenomicFeatureType] = Field(
        default=None,
        title="Feature",
        description="primary type of genomic feature being annotated",
    )
    is_download_only: Optional[bool] = Field(
        default=False,
        title="Download Only",
        description="File is available for download only; data cannot be queried using the NIAGADS Open Access API.",
    )
    data_source: Optional[str] = Field(
        default=None,
        title="Data Source",
        description="original data source for the track",
    )
    data_category: Optional[str] = Field(
        default=None,
        title="Category",
        description="data category; may be analysis type",
    )
    url: Optional[str] = Field(
        default=None,
        title="Download URL",
        description="URL for NIAGADS-standardized file",
    )

    @model_validator(mode="before")
    def extract_nested_fields(cls, values: Union[dict, any]):
        """
        Extract nested fields from ORM object and assign to top-level fields.

        Handles both ORM objects and dictionaries, extracting data_source
        from provenance, and url from file_properties.
        """
        if isinstance(values, dict):
            # Handle dictionary input
            provenance = values.get("provenance")
            if isinstance(provenance, dict):
                values.setdefault("data_source", provenance.get("data_source"))
            elif hasattr(provenance, "data_source"):  # ORM object
                values.setdefault("data_source", provenance.data_source)

            file_props = values.get("file_properties")
            if isinstance(file_props, dict):
                values.setdefault("url", file_props.get("url"))
            elif hasattr(file_props, "url"):  # ORM object
                values.setdefault("url", file_props.url)

        return values


class TrackMetadata(TrackRecord, ORMCompatabileMixin):
    id: str = Field(title="Track ID", description="stable track identifier")
    biosample_characteristics: Optional[BiosampleCharacteristicsReport] = Field(
        default=None,
        title="Sample Characteristics",
    )


class TrackResultMetrics(CountRecordModel):
    id: str = Field(
        title="Track ID",
        description="stable track identifier",
    )
