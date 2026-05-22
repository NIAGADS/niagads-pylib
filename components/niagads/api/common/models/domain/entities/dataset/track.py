from typing import List, Optional

from niagads.api.common.models.domain.base import ORMCompatibleRecord
from niagads.api.common.models.domain.mixins import (
    ORMCompatabileMixin,
    ResultMetricsMixin,
)
from niagads.common.genomic.features.models import GenomicFeatureType
from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.track.models import TrackRecord
from niagads.common.track.models.samples import BiosampleCharacteristics
from niagads.genome_reference.human import GenomeBuild
from pydantic import ConfigDict, Field


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


class TrackMetadata(TrackRecord, ORMCompatabileMixin):
    id: str = Field(title="Track ID", description="stable track identifier")
    biosample_characteristics: Optional[BiosampleCharacteristicsReport] = Field(
        default=None,
        title="Sample Characteristics",
    )


class TrackResultMetrics(CustomBaseModel, ResultMetricsMixin):
    id: str = Field(
        title="Track ID",
        description="stable track identifier",
    )
