from typing import Any, List, Optional, Union

from niagads.common.models.views.table import TableRow
from niagads.api_common.constants import DEFAULT_NULL_STRING
from niagads.api_common.models.core import DynamicRowModel
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.views.table import Table
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

    def table_fields(self, as_str=False, **kwargs):
        fields = self.get_model_fields(as_str)
        # FIXME: add _sort_fields?
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

            if isinstance(fields, list):
                fields.extend(list(extras.keys()))
                fields.append("track_id")
            else:
                fields.update(extras)
                fields.update(
                    {
                        "track_id": Field(
                            title="Track ID",
                            description="unique identifier for the source data track.",
                        )
                    }
                )

        return fields

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
            obj = self.model_dump()
            return [v for k, v in self.model_dump().items() if k in fields]

    def as_text(self, fields=None, null_str=".", **kwargs):
        if fields is None:
            fields = self.table_fields(as_str="true", **kwargs)
        values = self.as_list(fields=fields)
        return "\t".join([null_str if v is None else str(v) for v in values])

    def as_table_row(self, **kwargs):
        # do this way in case kwargs includes `extrasAsInfoStr`
        fields = self.table_fields(as_str=True, **kwargs)
        values = self.as_list(fields=fields)
        row = dict(zip(fields, values))
        return TableRow(**row)


class BEDResponse(RecordResponse):
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
        return self.to_text(includeHeader=False, null_str=".")

    def to_text(self, incl_header=True, null_str="NA"):
        """return a text response (e.g., BED, plain text)"""
        hasDynamicExtras = self.__has_dynamic_extras()

        if self.is_empty():
            if incl_header:
                # no data so have to get model fields from the class
                return self._get_empty_header()
            return ""

        else:
            fields = self.data[0].table_fields(
                as_str=True, extrasAsInfoStr=hasDynamicExtras
            )
            rows = []
            for r in self.data:
                rows.append(
                    r.as_text(fields=fields, null_str=null_str, extrasAsInfoStr=True)
                )
            responseStr = "\t".join(fields) + "\n" if incl_header else ""
            responseStr += "\n".join(rows)

        return responseStr
