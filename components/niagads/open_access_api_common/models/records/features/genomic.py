from typing import Optional

from niagads.genome.core import GenomicFeatureType, Human, Strand
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.types import Range
from pydantic import BaseModel, ConfigDict, field_serializer


class GenomicRegion(RowModel, Range):
    chromosome: Human
    strand: Optional[Strand] = None

    # so that strand does not get returned if missing
    model_config = ConfigDict(exclude_none=True)

    @field_serializer("chromosome")
    def serialize_group(self, chromosome: Human, _info):
        return str(chromosome)

    def __str__(self):
        span = f"{str(self.chromosome)}:{self.start}-{self.end}"
        if self.strand is not None:
            return f"{span:{str(self.strand)}}"
        else:
            return span


class Gene(RowModel):
    ensembl_id: str
    gene_symbol: Optional[str] = None


class Variant(RowModel):
    variant_id: str
    ref_snp_id: Optional[str] = None


class GenomicFeature(BaseModel):
    feature_id: str
    feature_type: GenomicFeatureType
