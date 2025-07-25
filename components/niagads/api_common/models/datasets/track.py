from typing import Any, Dict, List, Optional, Self, Union

from niagads.common.models.core import T_TransformableModel, TransformableModel
from niagads.database.schemas.dataset.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.api_common.constants import DEFAULT_NULL_STRING
from niagads.api_common.models.core import (
    ORMCompatibleDynamicRowModel,
    ORMCompatibleRowModel,
    ResultSize,
)
from niagads.api_common.models.response.core import RecordResponse
from niagads.utils.dict import promote_nested
from pydantic import Field, model_validator

COMPOSITE_ATTRIBUTES: Dict[str, T_TransformableModel] = {
    "biosample_characteristics": BiosampleCharacteristics,
    "subject_phenotypes": Phenotype,
    "experimental_design": ExperimentalDesign,
    "provenance": Provenance,
    "file_properties": FileProperties,
}


class AbridgedTrack(ORMCompatibleDynamicRowModel):
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
        exclude=True,
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


class Track(ORMCompatibleRowModel):
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
        exclude=True,
    )
    # FIXME: exclude cohorts until parsing resolved for FILER
    cohorts: Optional[List[str]] = Field(title="Cohorts")
    biosample_characteristics: Optional[BiosampleCharacteristics]
    subject_phenotypes: Optional[Phenotype]
    experimental_design: Optional[ExperimentalDesign]
    provenance: Optional[Provenance]
    file_properties: Optional[FileProperties]

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter)
        for field, value in self:
            if field in COMPOSITE_ATTRIBUTES.keys():
                del obj[field]
                if value is not None:
                    obj.update(value._flat_dump())
                else:
                    # create dict of {key: None}
                    obj.update(
                        {
                            k: None
                            for k in COMPOSITE_ATTRIBUTES[field].get_model_fields(
                                as_str=True
                            )
                        }
                    )

        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()
        model: T_TransformableModel
        for fieldId, model in COMPOSITE_ATTRIBUTES.items():
            fields.update(model.get_model_fields())

        for fieldId in COMPOSITE_ATTRIBUTES.keys():
            del fields[fieldId]

        return list(fields.keys()) if as_str else fields

    def as_table_row(self, **kwargs):
        return super().as_table_row(**kwargs)


class TrackResultSize(ResultSize):
    track_id: str = Field(title="Track ID", serialization_alias="id")


class AbridgedTrackResponse(RecordResponse):
    data: List[AbridgedTrack] = Field(
        description="Abridged metadata for each track meeting the query criteria.  Depending on query may include count of records matching query parameters."
    )


class TrackResponse(RecordResponse):
    data: List[Track] = Field(
        description="Full metadata for each track meeting the query criteria."
    )

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        if self.is_empty():
            if incl_header:
                return self._get_empty_header()
            else:
                return ""

        else:
            fields = self.data[0].get_fields(as_str=True)
            rows = []
            for r in self.data:
                if isinstance(r, str):
                    rows.append(r)
                else:
                    # pass fields to ensure consistent ordering
                    rows.append(r.as_text(fields=fields, null_str=null_str))

            response_str = "\t".join(fields) + "\n" if incl_header else ""
            response_str += "\n".join(rows)

        return response_str
