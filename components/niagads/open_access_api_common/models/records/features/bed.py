from typing import Any, List, Optional, Union

from niagads.open_access_api_common.models.records.core import DynamicRowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.core import id2title
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.utils.string import dict_to_info_string, xstr
from pydantic import Field


class BEDFeature(DynamicRowModel):
    chrom: str = Field(
        title="Chromosome", description="name of the chromosome or scaffold"
    )
    chromStart: int = Field(
        title="Start",
        description="starting position of the feature in the chromosomse. 0-based",
    )
    chromEnd: int = Field(
        title="End",
        description="ending position of the feature; not included in the display",
    )
    name: Optional[str] = Field(
        title="Name", default=".", description="display label for the feature"
    )
    score: Optional[Union[str, int, float]] = Field(
        title="Score", default=".", description="a score between 0 and 1000"
    )
    strand: Optional[str] = Field(
        title="Strand", default=".", description="forward (+) or reverse (-) direction"
    )

    def get_field_names(self, collapseExtras: bool):
        return list(self.model_fields.keys()) + self.get_extra_fields(collapseExtras)

    def get_extra_fields(self, collapseExtras: bool):
        """get list of valid fields"""
        if isinstance(self.model_extra, dict):
            if len(self.model_extra) > 0:
                if collapseExtras:
                    fields = ["other_annotations"]
                else:
                    fields = [k for k in self.model_extra.keys() if k != "track_id"]

        return fields + ["track_id"]

    def add_track(self, trackId: Any):
        self.model_extra["track_id"] = trackId

    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get("nullStr", ".")
        data = self.__get_row_data(kwargs.get("collapseExtras", False))
        return "\t".join(
            [xstr(value, nullStr=nullStr, dictsAsJson=False) for value in data.values()]
        )

    def __get_row_data(self, collapseExtras: bool):
        if collapseExtras:
            data: dict = {
                k: v
                for k, v in self.model_dump().items()
                if k in list(self.model_fields.keys())
            }
            extraData = {
                k: v
                for k, v in self.model_dump().items()
                if k in list(self.model_extra.keys()) and k != "track_id"
            }
            data.update(
                {
                    "other_annotations": dict_to_info_string(extraData),
                    "track_id": self.track_id,
                }
            )
            return data
        else:
            return self.model_dump()

    def to_view_data(self, view: ResponseView, **kwargs):
        match view:
            case view.TABLE:
                return self.__get_row_data(kwargs.get("collapseExtras", False))
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def _generate_table_columns(self, model, **kwargs):
        columns = super()._generate_table_columns(model)
        extras = self.get_extra_fields(kwargs.get("collapseExtras", False))
        extraColumns: List[dict] = [{"id": f, "header": f} for f in extras]
        return {"columns": columns + extraColumns}

    def _get_table_view_config(self, **kwargs):
        return super()._get_table_view_config(**kwargs)

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        match view:
            case view.TABLE:
                return self._get_table_view_config(kwargs)
            # case view.IGV_BROWSER:
            #    return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )


class BEDResponse(GenericResponse):
    data: List[BEDFeature]

    def __has_dynamic_extras(self) -> bool:
        """test to see if rows have different additional fields"""
        extras = set()

        row: BEDFeature
        for row in self.data:
            if row.has_extras():
                if len(extras) == 0:
                    extras = set(row.model_extra.keys())
                else:
                    dynamicExtras = extras != set(row.model_extra.keys())
                    if dynamicExtras:
                        return True

        return False

    def to_text(self, format: ResponseFormat, **kwargs):
        """return a text response (e.g., BED, plain text)"""
        hasDynamicExtras = self.__has_dynamic_extras()

        fields = (
            self.data[0].get_field_names(collapseExtras=hasDynamicExtras)
            if len(self.data) > 0
            else BEDFeature.get_model_fields()
        )

        return super().to_text(
            format, fields=fields, collapseExtras=hasDynamicExtras, **kwargs
        )
