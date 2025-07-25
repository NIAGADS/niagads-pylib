from typing import Optional
from niagads.api_common.models.core import RowModel
from niagads.api_common.models.features.genomic import GenomicRegion
from niagads.api_common.models.features.variant import Variant
from niagads.database.schemas.variant.composite_attributes import PredictedConsequence
from pydantic import Field, field_validator


class RV(Variant):
    most_severe_consequence: Optional[PredictedConsequence] = Field(
        default=None,
        title="Predicted Consequence",
        description="most severe consequence predicted by VEP",
    )

    @field_validator("most_severe_consequence", mode="before")
    @classmethod
    def parse_most_severe_consequence(cls, v):
        if v is None:
            return None
        if not isinstance(v, dict):  # ORM response
            v = v.model_dump()
        try:
            conseq = PredictedConsequence(**v)
            return conseq
        except:
            return PredictedConsequence.from_vep_json(v)

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["most_severe_consequence"]
        if self.most_severe_consequence is not None:
            obj.update(self.most_severe_consequence._flat_dump())
        else:
            obj.update(
                {k: None for k in PredictedConsequence.get_model_fields(as_str=True)}
            )
        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()

        del fields["most_severe_consequence"]
        fields.update(PredictedConsequence.get_model_fields())

        return list(fields.keys()) if as_str else fields


class RegionVariant(RowModel):
    variant: RV = Field(title="Variant")
    variant_type: str = Field(
        title="Variant Type", description="structural or smal variant"
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
        fields.update(RV.get_model_fields())

        return list(fields.keys()) if as_str else fields
