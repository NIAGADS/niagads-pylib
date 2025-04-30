from typing import List, Optional

from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    Phenotype,
)
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.response.core import ResponseModel
from niagads.open_access_api_common.models.views.core import id2title
from niagads.open_access_api_common.models.views.table.core import TableViewModel
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from pydantic import Field, computed_field, field_validator


class IGVBrowserTrackConfig(RowModel):
    track_id: str = Field(serialization_alias="id")
    name: str
    url: str
    description: str
    type: str
    format: str

    browser_track_type: str = Field(serialization_alias="type")
    browser_track_format: str = Field(serialization_alias="format")
    infoURL: str = Settings.from_env().IGV_BROWSER_INFO_URL

    @field_validator("format", mode="before")
    def extract_track_format(self, fileSchema) -> str:
        """extract file schema from file format"""
        if fileSchema is None:
            return "bed"
        schema = fileSchema.split("|")
        return schema[0]

    @field_validator("type", mode="before")
    def extract_track_type(self, fileSchema) -> str:
        """extract track type from file schema"""

        if "|" in fileSchema:
            schema = fileSchema.split("|")
            return schema[1]
        return "annotation"

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
        return self.browser_track_type == "qtl"

    # model_config = ConfigDict(populate_by_name=True)

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        return None

    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump(by_alias=True)

    def to_text(self, format: ResponseFormat, **kwargs):
        return super().to_text(format, **kwargs)


# sole purpose of this model is to assemble the information for the track selector
class IGVBrowserTrackMetadata(RowModel):
    track_id: str
    name: str
    description: str
    data_source: str
    feature_type: str  # = Field(serialization_alias='feature')
    biosample_characteristics: Optional[BiosampleCharacteristics] = None
    experimental_design: Optional[ExperimentalDesign] = None
    subject_phenotypes: Optional[Phenotype] = None

    # model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def get_table_columns(self):
        fields = list(self.model_fields.keys())
        columns: List[dict] = [
            {"id": f, "header": id2title(f)}
            for f in fields
            if f not in ["biosample_characteristics", "experimental_design"]
        ]
        columns += [
            {"id": f, "header": id2title(f)}
            for f in BiosampleCharacteristics.model_fields
        ]
        columns += [
            {"id": f, "header": id2title(f)} for f in ExperimentalDesign.model_fields
        ]

        return columns

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


class IGVBrowserTrackConfigResponse(ResponseModel):
    data: List[IGVBrowserTrackConfig]


class IGVBrowserTrackSelectorResponse(ResponseModel):
    data: TableViewModel

    @classmethod
    def build_table(cls, metadata: RowModel, tableId: str):
        tableData = []
        track: RowModel
        for track in metadata:
            rowData = track.serialize()
            rowData = IGVBrowserTrackMetadata(**rowData)
            tableData.append(rowData.serialize(promoteObjs=True, byAlias=True))

        columns = IGVBrowserTrackMetadata.get_table_columns()
        options = IGVBrowserTrackMetadata.get_table_options()
        options.update({"defaultColumns": [c["id"] for c in columns[:8]]})

        return {
            "data": tableData,
            "columns": columns,
            "options": options,
            "id": tableId,
        }
