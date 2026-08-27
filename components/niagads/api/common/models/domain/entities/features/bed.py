from typing import Any, Optional, Union

from niagads.api.common.models.domain.base import DynamicRecordModel
from niagads.utils.string import dict_to_info_string, xstr
from pydantic import Field


class BEDFeature(DynamicRecordModel):
    chrom: str = Field(title="Chromosome", description="name of the chromosome")
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

    @property
    def track_id(self):
        if self.has_extras() and "track_id" in self.model_extra:
            return self.model_extra["track_id"]
        return None

    def get_model_fields(self, sort=False, collapse_extras: bool = True):
        if not collapse_extras:
            return super().get_model_fields(sort)

        # get fields, ignore those set to exclude=True
        fields: dict = [
            (k, v)
            for k, v in self.__class__.model_fields.items()
            if not getattr(v, "exclude", False)
        ]
        if sort:
            fields = sorted(
                fields,
                key=lambda item: (item[1].json_schema_extra or {}).get(
                    "order", float("inf")
                ),
            )

        field_names = list(fields.keys())

        if self.track_id is not None:
            field_names.append("track_id")
        if self.has_extras() and len(self.model_extra.keys() > 1):
            field_names.append("other_info")

    def add_track(self, track_id: Any):
        self.model_extra["track_id"] = track_id

    def __serialize_extras(self):
        extras = {
            k: v
            for k, v in self.model_dump().items()
            if k in list(self.model_extra.keys()) and k != "track_id"
        }
        return dict_to_info_string(extras) if len(extras) > 0 else None

    def to_value_list(self, fields=None, collapse_extras: bool = False):
        if fields is not None:
            sorted_fields = fields
        else:
            if collapse_extras:
                sorted_fields = self.__class__.get_model_fields_from_class(sort=False)
            else:
                sorted_fields = self.get_model_fields(sort=False)

        data = self.clean_model_dump(exclude_none=False)
        values = [data.get(f) for f in sorted_fields]

        if self.has_extras() and collapse_extras:
            info = self.__serialize_extras()
            track_id = self.track_id

            if track_id:
                values.append(track_id)

            if info:
                values.append(info)

        return values

    def to_BED(self, incl_header: bool = False):
        delimiter = "\t"
        values = self.to_value_list(collapse_extras=False)
        delimited_text = delimiter.join([xstr(v, null_str=".") for v in values])

        if incl_header:
            fields = self.get_model_fields(sort=False)
            header = delimiter.join(fields)
            delimited_text = "\n".join([header, delimited_text])

        return delimited_text

    def to_delimited_text(
        self, fields=None, incl_header=False, null_str="NA", delimiter="\t"
    ):
        return self.to_BED(incl_header=incl_header)
