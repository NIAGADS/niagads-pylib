from typing import Any, Dict, List, Optional, Self, Union

from niagads.common.models.core import OntologyTerm
from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.open_access_api_common.models.records.core import DynamicRowModel, RowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.core import id2title
from niagads.open_access_api_common.models.views.table.core import TableColumn
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.utils.dict import promote_nested
from niagads.utils.list import find
from pydantic import ConfigDict, Field, computed_field, model_validator

EXCLUDE_FROM_TRACK_VIEWS = [
    "ontology",
    "definition",
    "biosample",
    "biosample_characteristics",
    "subject_phenotypes",
    "experimental_design",
    "provenance",
    "file_properties",
]


class AbridgedTrack(DynamicRowModel):
    track_id: str = Field(title="Track")
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
        promote_nested(
            data, updateByReference=True
        )  # should make data_source, url etc available

        # filter out excess from the Track ORM model
        modelFields = AbridgedTrack.model_fields.keys()
        return {
            k: v for k, v in data.items() if k in modelFields or k.startswith("num_")
        }


class Track(RowModel):
    track_id: str = Field(title="Track")
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
    cohorts: Optional[List[str]] = Field(title="Cohorts", exclude=True)
    biosample_characteristics: Optional[BiosampleCharacteristics]
    subject_phenotypes: Optional[Phenotype]
    experimental_design: Optional[ExperimentalDesign]
    provenance: Optional[Provenance]
    file_properties: Optional[FileProperties]

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)

    def to_view_data(self, view: ResponseView, **kwargs):
        row: dict = super().to_view_data(view, **kwargs)

        if view == ResponseView.TABLE:
            promote_nested(row, updateByReference=True)
            # FIXME: front-end?

            row.update({"term": row["biosample"][0]["term"]})
            if "term_id" in row["biosample"]:
                row.update({"term_id": row["biosample"][0]["term_id"]})
            else:
                row.update({"term_id": None})

            orderedRow = {}
            for field in kwargs["fields"]:
                if field not in row:
                    orderedRow.update({field: None})
                else:
                    orderedRow.update({field: row[field]})

            return orderedRow
        else:
            return row

    def _get_table_view_config(self, **kwargs):
        columns = super()._get_table_view_config(**kwargs)["columns"]

        # add biosample, provenance, experimental design, file properties
        columns += self._generate_table_columns(BiosampleCharacteristics)
        columns += self._generate_table_columns(OntologyTerm)
        columns += self._generate_table_columns(Phenotype)
        columns += self._generate_table_columns(ExperimentalDesign)
        columns += self._generate_table_columns(Provenance)
        columns += self._generate_table_columns(FileProperties)

        columns = [c for c in columns if c.id not in EXCLUDE_FROM_TRACK_VIEWS]

        # NOTE: options are handled in front-end applications
        return {"columns": columns}


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


class AbridgedTrackResponse(GenericResponse):
    data: List[AbridgedTrack] = Field(
        description="Abridged metadata for each track meeting the query criteria.  Depending on query may include count of records matching query parameters."
    )

    def to_text(self, format: ResponseView, **kwargs):
        fields = (
            self.data[0].get_instantiated_fields()
            if len(self.data) > 0
            else AbridgedTrack.get_model_fields()
        )
        return super().to_text(format, fields=fields)


class TrackResponse(GenericResponse):
    data: List[Track] = Field(
        description="Full metadata for each track meeting the query criteria."
    )

    def to_text(self, format: ResponseView, **kwargs):
        fields = AbridgedTrack.get_model_fields()
        return super().to_text(format, fields=fields)
