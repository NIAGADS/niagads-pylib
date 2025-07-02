from typing import Any, Dict, List, Optional, Self, Union

from niagads.common.models.ontology import OntologyTerm
from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.open_access_api_common.models.core import DynamicRowModel, RowModel
from niagads.open_access_api_common.models.response.core import RecordResponse

from niagads.utils.dict import promote_nested
from pydantic import ConfigDict, Field, model_validator


class AbridgedTrack(DynamicRowModel):
    track_id: str = Field(title="Track", serialization_alias="id")
    name: str = Field(title="Name")
    description: Optional[str] = Field(default=None, title="Description")
    genome_build: str = Field(title="Genome Build")
    feature_type: Optional[str] = Field(default=None, title="Feature")
    is_download_only: Optional[bool] = Field(
        default=False,
        title="Download Only",
        description="File is available for download only; data cannot be queried using the NIAGADS Open Access API.",
    )
    is_shard: Optional[bool] = Field(
        default=False,
        title="Is Shard?",
        description="Flag indicateing whether track is part of a result set sharded by chromosome.",
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

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def process_extras(cls: Self, data: Union[Dict[str, Any]]):
        """
        promoted nested fields so that can get data_source, data_category,
        url, etc from `Track` object

        not doing null checks b/c if these values are missing there is an
        error in the data the needs to be reviewed

        After promotion, only keep extra counts, prefixed with `num_` as
        allowable extra fields for a track summary
        """

        # this will happen b/c FastAPI tries all models
        # until it can successfully serialize
        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            data = data.model_dump()  # assume data is an ORM w/model_dump mixin

        # should make data_source, url etc available
        promote_nested(data, updateByReference=True)

        # filter out excess from the Track ORM model
        modelFields = AbridgedTrack.model_fields.keys()
        return {
            k: v for k, v in data.items() if k in modelFields or k.startswith("num_")
        }


class Track(RowModel):
    track_id: str = Field(title="Track", serialization_alias="id")
    name: str = Field(title="Name")
    description: Optional[str] = Field(default=None, title="Description")
    genome_build: str = Field(title="Genome Build")
    feature_type: Optional[str] = Field(default=None, title="Feature")
    is_download_only: Optional[bool] = Field(
        title="Download Only",
        description="File is available for download only; data cannot be queried using the NIAGADS Open Access API.",
    )
    is_shard: Optional[bool] = Field(
        title="Is Shard?",
        description="Flag indicateing whether track is part of a result set sharded by chromosome.",
    )
    # FIXME: exclude cohorts until parsing resolved for FILER
    cohorts: Optional[List[str]] = Field(title="Cohorts")
    biosample_characteristics: Optional[BiosampleCharacteristics]
    subject_phenotypes: Optional[Phenotype]
    experimental_design: Optional[ExperimentalDesign]
    provenance: Optional[Provenance]
    file_properties: Optional[FileProperties]

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)

    def table_fields(self, asStr=False, **kwargs):
        return super().table_fields(asStr, **kwargs)

    def as_info_string(self):
        return super().as_info_string()

    def as_list(self, fields=None):
        return super().as_list(fields)

    def as_table_row(self, **kwargs):
        return super().as_table_row(**kwargs)


class TrackResultSize(RowModel):
    track_id: str = Field(title="Track ID", serialization_alias="id")
    num_results: int = Field(
        title="Num. Results",
        description="Number of results (hits or overlaps) on this track within the query region and meeting any filter criteria.",
    )

    def __str__(self):
        return self.as_info_string()

    @staticmethod
    def sort(results: List[Self], reverse=True) -> List[Self]:
        """sorts a list of track results"""
        return sorted(results, key=lambda item: item.num_results, reverse=reverse)


class AbridgedTrackResponse(RecordResponse):
    data: List[AbridgedTrack] = Field(
        description="Abridged metadata for each track meeting the query criteria.  Depending on query may include count of records matching query parameters."
    )


class TrackResponse(RecordResponse):
    data: List[Track] = Field(
        description="Full metadata for each track meeting the query criteria."
    )
