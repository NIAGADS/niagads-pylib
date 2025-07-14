from typing import Any, Dict, List, Optional, Self, Union

from niagads.common.models.ontology import OntologyTerm
from niagads.database.schemas.dataset.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    Phenotype,
    Provenance,
)
from niagads.api_common.config import Settings
from niagads.api_common.models.core import RowModel
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.views.table import Table
from niagads.utils.dict import promote_nested
from pydantic import ConfigDict, Field, computed_field, field_validator, model_validator

EXCLUDE_FROM_METADATA = [
    "ontology",
    "definition",
    "biosample",
    "biosample_characteristics",
    "subject_phenotypes",
    "experimental_design",
    "provenance",
    "file_properties",
    "release_version",
    "release_date",
    "download_date",
    "download_url",
    "accession",
    "pubmed_id",
    "doi",
    "attribution",
]


class IGVBrowserTrackConfig(RowModel):
    track_id: str = Field(serialization_alias="id")
    name: str
    url: str
    description: str
    file_schema: str = Field(exclude=True)
    infoURL: str = Settings.from_env().IGV_BROWSER_INFO_URL

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

        After promotion, only keep extra counts, prefixed with `num_`
        allowable extra fields for a track summary
        """

        # this will happen b/c FastAPI tries all models
        # until it can successfully serialize
        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            data = data.model_dump()  # assume data is an ORM w/model_dump mixin

        promote_nested(data, attributes="file_properties", updateByReference=True)

        # filter out excess from the Track ORM model
        modelFields = IGVBrowserTrackConfig.model_fields.keys()
        return {k: v for k, v in data.items() if k in modelFields}

    @computed_field
    @property
    def format(self) -> str:
        """extract file schema from file format"""
        if self.file_schema is None:
            return "bed"
        schema = self.file_schema.split("|")
        return schema[0]

    @computed_field
    @property
    def type(self) -> str:
        """extract track type from file schema"""
        if self.file_schema is None or "|" not in self.file_schema:
            return "annotation"

        schema = self.file_schema.split("|")
        return schema[1]

    @computed_field
    @property
    def indexURL(self) -> str:
        if self.url.endswith(".gz"):
            return self.url + ".tbi"
        else:
            return None

    @computed_field
    @property
    def autoscale(self) -> bool:
        return self.type == "qtl"

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        return None

    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump(by_alias=True)

    def to_text(self, format: ResponseFormat, **kwargs):
        return super().to_text(format, **kwargs)


# sole purpose of this model is to assemble the information for the track selector
class IGVBrowserTrackMetadata(RowModel):
    track_id: str = Field(title="Track")
    name: str = Field(title="Name")
    description: str = Field(Title="Description")
    data_source: str = Field(title="Data Source")
    feature_type: str = Field(title="Feature Type")
    biosample_characteristics: Optional[BiosampleCharacteristics] = None
    experimental_design: Optional[ExperimentalDesign] = None
    subject_phenotypes: Optional[Phenotype] = None

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

        # get the provenance fields, but leave the rest as dicts
        promote_nested(
            data, attributes="provenance", updateByReference=True
        )  # should make data_source, url etc available

        # filter out excess from the Track ORM model
        modelFields = IGVBrowserTrackMetadata.model_fields.keys()
        return {k: v for k, v in data.items() if k in modelFields}

    def _get_table_view_config(self, **kwargs):
        columns = super()._get_table_view_config(**kwargs)["columns"]

        # add biosample, provenance, experimental design, file properties
        columns += self._generate_table_columns(BiosampleCharacteristics)
        columns += self._generate_table_columns(OntologyTerm)
        columns += self._generate_table_columns(Phenotype)
        columns += self._generate_table_columns(ExperimentalDesign)
        # need to remove data_source to avoid duplicate
        columns += [
            c for c in self._generate_table_columns(Provenance) if c.id != "data_source"
        ]

        columns = [c for c in columns if c.id not in EXCLUDE_FROM_METADATA]

        # NOTE: options are handled in front-end applications
        return {"columns": columns}

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

    @classmethod
    def get_table_options(self):
        options: dict = {
            "rowSelect": {
                "header": "Add/Remove Track",
                "enableMultiRowSelect": True,
                "rowId": "track_id",
                # "onRowSelectAction": str(OnRowSelect.UPDATE_GENOME_BROWSER),
            },
        }
        return options

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        return None


class IGVBrowserTrackConfigResponse(RecordResponse):
    data: List[IGVBrowserTrackConfig]


class IGVBrowserTrackSelectorResponse(RecordResponse):
    data: Table

    @classmethod
    def build_table(cls, metadata: RowModel, tableId: str):
        config = {}
        tableData = []
        track: RowModel
        for index, track in enumerate(metadata):
            rowData = IGVBrowserTrackMetadata(**(track.model_dump()))
            if index == 0:
                config = rowData._get_table_view_config()
                fieldIds = [c.id for c in config["columns"]]

            tableData.append(rowData.to_view_data(ResponseView.TABLE, fields=fieldIds))

        options = IGVBrowserTrackMetadata.get_table_options()

        return {
            "data": tableData,
            "columns": config["columns"],
            "options": options,
            "id": tableId,
        }
