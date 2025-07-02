from typing import Any, List, Optional, Union

from niagads.common.models.views.table import TableRow
from niagads.open_access_api_common.config.constants import DEFAULT_NULL_STRING
from niagads.open_access_api_common.models.core import DynamicRowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.views.table import Table
from niagads.utils.string import dict_to_info_string
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

    def add_track(self, trackId: Any):
        self.model_extra["track_id"] = trackId

    def table_fields(self, asStr=False, **kwargs):
        fields = super().get_fields(asStr)
        if self.has_extras():
            if getattr(kwargs, "extrasAsInfoStr", False):
                extras = {
                    "additional_annotations": Field(
                        title="Additional Annotation",
                        desription="extended BED annotations",
                    )
                }
            else:
                extras = {
                    k: Field() for k in self.model_extra.keys() if k != "track_id"
                }
            fields.update(extras)
            fields.update(
                {
                    "track_id": Field(
                        title="Track ID",
                        description="unique identifier for the source data track.",
                    )
                }
            )

        return list(fields.keys()) if asStr else fields

    def get_fields(self, asStr: bool = False):
        fields = super().get_fields(asStr)
        if self.has_extras():
            extras = {k: Field() for k in self.model_extra.keys() if k != "track_id"}
            fields.update(extras)
            fields.update(
                {
                    "track_id": Field(
                        title="Track ID",
                        description="unique identifier for the source data track.",
                    )
                }
            )

        return list(fields.keys()) if asStr else fields

    def __extras_as_info_str(self):
        extras = {
            k: v
            for k, v in self.model_dump().items()
            if k in list(self.model_extra.keys()) and k != "track_id"
        }
        return dict_to_info_string(extras)

    def as_list(self, fields=None):
        if fields is None:
            return list(self.model_dump().values())
        elif "additional_annotations" in fields:
            obj = self.model_dump()
            values = [
                v for k, v in obj if k in list(self.__class__.model_fields.keys())
            ]
            values.append(self.__extras_as_info_str(), values.append(obj["track_id"]))
            return values
        else:
            return [v for k, v in self.model_dump() if k in fields]

    def as_text(self, fields=None, nullStr=".", **kwargs):
        if fields is None:
            fields = self.table_fields(asStr="true", **kwargs)
        values = self.as_list(fields=fields)
        return "\t".join([nullStr if v is None else str(v) for v in values])

    def as_table_row(self, **kwargs):
        # do this way in case kwargs includes `extrasAsInfoStr`
        fields = self.table_fields(asStr=True, **kwargs)
        values = self.as_list(fields=fields)
        row = dict(zip(fields, values))
        return TableRow(**row)


class BEDResponse(GenericResponse):
    data: List[BEDFeature]

    def __has_dynamic_extras(self) -> bool:
        """test to see if rows have different additional fields"""
        extras = set()

        for row in self.data:
            if row.has_extras():
                if len(extras) == 0:
                    extras = set(row.model_extra.keys())
                else:
                    if extras != set(row.model_extra.keys()):
                        return True

        return False

    def to_table(self, id=None, title=None):
        if self.is_empty():
            return {}

        else:
            hasDynamicExtras = self.__has_dynamic_extras()
            columns = self.data[0].table_columns(extrasAsInfoStr=hasDynamicExtras)
            data = [
                r.as_table_row(hasDynamicExtras=hasDynamicExtras) for r in self.data
            ]
            table = {"columns": columns, "data": data}

            if title is not None:
                table.update({"title", title})
            if id is not None:
                table.update({"id": id})

            return Table(**table)

    def to_bed(self):
        return self.to_text(includeHeader=True, nullStr=".")

    def to_text(self, inclHeader=True, nullStr=DEFAULT_NULL_STRING):
        """return a text response (e.g., BED, plain text)"""
        hasDynamicExtras = self.__has_dynamic_extras()

        if self.is_empty():
            if inclHeader:
                # no data so have to get model fields from the class
                return self._get_empty_header()
            return ""

        else:
            fields = self.data[0].table_fields(
                asStr=True, extrasAsInfoStr=hasDynamicExtras
            )
            rows = []
            for r in self.data:
                rows.append(
                    "\t".join(
                        r.as_text(fields=fields, nullStr=nullStr, extrasAsInfoStr=True)
                    )
                )
            responseStr = "\t".join(fields) + "\n" if inclHeader else ""
            responseStr += "\n".join(rows)

        return responseStr
