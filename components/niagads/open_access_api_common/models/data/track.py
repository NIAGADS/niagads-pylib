from typing import Any, Dict, List, Optional, Self, Union

from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.open_access_api_common.models.data.core import DynamicRowModel
from niagads.open_access_api_common.models.views.core import id2title
from niagads.open_access_api_common.parameters.response import ResponseView
from niagads.utils.list import find
from pydantic import model_validator
from sqlalchemy import RowMapping


class GenericTrackSummary(DynamicRowModel):
    track_id: str
    name: str
    description: Optional[str] = None
    genome_build: Optional[str] = None
    feature_type: Optional[str] = None
    data_source: Optional[str] = None
    data_category: Optional[str] = None
    url: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def allowable_extras(cls: Self, data: Union[Dict[str, Any]]):
        """for now, allowable extras are just counts, prefixed with `num_`"""
        ## FIXME
        if not type(data) == RowMapping:
            if (
                # type(data).__base__ == SQLModel
                # or
                isinstance(data, str)
                or not isinstance(data, dict)
            ):
                # then there are no extra fields or FASTAPI is attempting to serialize
                # unnecessarily when returning a Union[ResponseType Listing]
                return data
        modelFields = cls.model_fields.keys()
        return {
            k: v for k, v in data.items() if k in modelFields or k.startswith("num_")
        }

    def get_field_names(self):
        fields = list(self.model_fields.keys())
        if isinstance(self.model_extra, dict):
            if len(self.model_extra) > 0:
                fields += list(self.model_extra.keys())
        return fields

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        match view:
            case view.TABLE:
                return self._build_table_config()
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def to_view_data(self, view: ResponseView, **kwargs):
        """covert row data to view formatted data"""
        return self.serialize()

    def _build_table_config(self):
        """Return a column object for niagads-viz-js/Table"""
        fields = self.get_field_names()
        columns: List[dict] = [{"id": f, "header": id2title(f)} for f in fields]

        # update type of is_lifted to boolean
        index: int = find(columns, "is_lifted", "id", returnValues=False)
        columns[index[0]].update(
            {
                "type": "boolean",
                "description": "data have been lifted over from an earlier genome build",
            }
        )

        # update url to link
        index: int = find(columns, "url", "id", returnValues=False)
        columns[index[0]].update({"type": "link"})

        options = {}
        if "num_overlaps" in fields:
            options.update(
                {
                    "rowSelect": {
                        "header": "Select",
                        "enableMultiRowSelect": True,
                        "rowId": "track_id",
                        # "onRowSelectAction": OnRowSelect.ACCESS_ROW_DATA,
                    }
                }
            )
            fields.remove("num_overlaps")
            fields.insert(
                0, "num_overlaps"
            )  # so that it is in the first 8 and displayed by default
        if len(fields) > 8:
            options.update({"defaultColumns": fields[:8]})
        return {"columns": columns, "options": options}


class GenericTrack(GenericTrackSummary):
    experimental_design: Optional[ExperimentalDesign] = None
    biosample_characteristics: Optional[BiosampleCharacteristics] = None
    provenance: Optional[Provenance] = None
    subject_phenotypes: Optional[Phenotype] = None
    file_properties: Optional[FileProperties] = None

    def to_view_data(self, view: ResponseView, **kwargs):
        return self.serialize(promoteObjs=True)
