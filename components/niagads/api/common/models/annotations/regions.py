from niagads.api.common.models.core import RowModel
from niagads.api.common.models.features.region import GenomicRegion
from niagads.api.common.models.features.variant import AbridgedVariant
from pydantic import Field


class RegionVariant(RowModel):
    variant: AbridgedVariant = Field(title="Variant")
    variant_type: str = Field(
        title="Variant Type", description="structural or small variant"
    )
    location: GenomicRegion
    range_relation: str = Field(
        title="Range Relation",
        description="indicates location of gene relative to the queries region",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["location"]
        obj.update(self.location._flat_dump())

        del obj["variant"]
        obj.update(self.variant._flat_dump())

        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()

        del fields["location"]
        fields.update(GenomicRegion.get_model_fields())

        del fields["variant"]
        fields.update(AbridgedVariant.get_model_fields())

        return list(fields.keys()) if as_str else fields
