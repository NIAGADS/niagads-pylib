from typing import Any, ClassVar, Dict, List, Optional, Self, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.data_models.mixins import ORMCompatabileMixin, ResultSizeMixin
from niagads.common.models.base import CustomBaseModel
from niagads.common.track.models import TrackRecord

from niagads.common.genomic.features.models import GenomicFeatureType
from niagads.genome_reference.human import GenomeBuild
from niagads.utils.dict import promote_nested
from pydantic import ConfigDict, Field, model_validator


class TrackSummary(CustomBaseModel, ORMCompatabileMixin):
    model_config = ConfigDict(is_summary=True)

    id: str = Field(
        title="Track ID",
        description="stable track identifier",
    )
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


class Track(TrackRecord, ORMCompatabileMixin): ...


class TrackResultSize(CustomBaseModel, ResultSizeMixin):
    id: str = Field(
        title="Track ID",
        description="stable track identifier",
    )
