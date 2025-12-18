from typing import Optional
from niagads.api.common.models.core import RowModel
from niagads.genomics.features.region.core import GenomicRegion as __BaseGenomicRegion
from pydantic import Field


class GenomicRegion(RowModel, __BaseGenomicRegion):
    max_range_size: Optional[int] = Field(default=None, exclude=True)

    def as_info_string(self):
        raise NotImplementedError("TODO when required")

    def __str__(self):
        span = f"{str(self.chromosome)}:{self.start}-{self.end}"
        # if self.strand is not None:
        #    return f"{span}:{str(self.strand)}"
        # else:
        return span

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()
        order = [
            "chr",  # have to use serialization alias
            "start",
            "end",
            "strand",
            "length",
        ]
        ordered_fields = {k: fields[k] for k in order}
        return list(ordered_fields.keys()) if as_str else ordered_fields
