from typing import Any, Dict, List, Optional, Self, Union

from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.open_access_api_common.models.records.core import DynamicRowModel, RowModel
from niagads.open_access_api_common.models.response.core import PagedResponseModel
from niagads.open_access_api_common.models.views.core import id2title
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.utils.dict import promote_nested
from niagads.utils.list import find
from pydantic import ConfigDict, Field, computed_field, model_validator


class TrackSummary(DynamicRowModel):
    track_id: str
    name: str
    description: Optional[str] = None
    genome_build: Optional[str] = None
    feature_type: Optional[str] = None
    data_source: Optional[str] = None
    data_category: Optional[str] = None
    url: Optional[str] = None

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_nested_fields(cls: Self, data: Union[Dict[str, Any], Any]):
        """
        promoted nested fields so that can get data_source, data_category,
        url, etc from `Track` object

        not doing null checks b/c if these values are missing there is an
        error in the data the needs to be reviewed
        """
        if isinstance(data, dict):
            newDataObj = promote_nested(data, False)
        else:  # a `Track` ORM with a model_dump mixin
            newDataObj = promote_nested(data.model_dump(), False)
        return newDataObj

    @model_validator(mode="before")
    @classmethod
    def allowable_extras(cls: Self, data: Union[Dict[str, Any]]):
        """for now, allowable extras are just counts, prefixed with `num_`"""
        modelFields = TrackSummary.model_fields.keys()
        return {
            k: v for k, v in data.items() if k in modelFields or k.startswith("num_")
        }


class Track(RowModel):
    track_id: str = Field(title="Track")
    name: str = Field(title="Name")
    description: Optional[str] = Field(title="Description")
    genome_build: str = Field(title="Genome Build")
    feature_type: Optional[str] = Field(title="Feature")
    is_download_only: Optional[bool] = Field(
        title="Download Only",
        description="File is available for download only; data cannot be queried using the NIAGADS Open Access API.",
    )
    is_shard: Optional[bool] = Field(
        title="Is Shard?",
        description="Flag indicateing whether track is part of a result set sharded by chromosome.",
    )
    cohorts: Optional[List[str]] = Field(title="Cohorts")
    biosample_characteristics: Optional[BiosampleCharacteristics]
    subject_phenotypes: Optional[Phenotype]
    experimental_design: Optional[ExperimentalDesign]
    provenance: Optional[Provenance]
    file_properties: Optional[FileProperties]

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)

    """
    # this should be deprecated in Pydantic v2+
    class Config:
        orm_mode = True
    """


class TrackResultSize(RowModel):
    track_id: str = Field(title="track")
    num_results: int = Field(
        title="Num. Results",
        description="Number of results (hits or overlaps) on this track within the query region and meeting any filter criteria.",
    )

    def get_view_config(self, view: ResponseView, **kwargs):
        raise RuntimeError("View transformations not implemented for this row model.")

    def to_view_data(self, view: ResponseView, **kwargs):
        raise RuntimeError("View transformations not implemented for this row model.")

    def to_text(self, format: ResponseFormat, **kwargs):
        return f"{self.track_id}\t{self.num_results}"

    @staticmethod
    def sort(results: List[Self], reverse=True) -> List[Self]:
        """sorts a list of track results"""
        return sorted(results, key=lambda item: item.num_results, reverse=reverse)


class TrackSummaryResponse(PagedResponseModel):
    data: List[TrackSummary]

    def to_text(self, format: ResponseView, **kwargs):
        fields = (
            self.response[0].get_field_names()
            if len(self.response) > 0
            else TrackSummary.get_model_fields()
        )
        return super().to_text(format, fields=fields)


class TrackResponse(PagedResponseModel):
    data: List[Track]

    def to_text(self, format: ResponseView, **kwargs):
        fields = Track.get_model_fields()
        return super().to_text(format, fields=fields)
