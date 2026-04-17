from typing import Optional

from niagads.common.gene.models.record import GeneIdentifier
from niagads.common.models.base import CustomBaseModel

from niagads.common.variant.models.record import VariantIdentifier

from pydantic import Field


# list of track_metadata at top level, so its not repeated multiple times


# FIXME: move to span/region?
class LocusContext(CustomBaseModel):
    locus_range: Optional[str] = Field(default=None, title="Locus Range")
    locus_id: Optional[str] = Field(default=None, title="Locus ID")


class GenePrioritization(CustomBaseModel):
    gene: GeneIdentifier = Field(title="Gene")
    variant: VariantIdentifier = Field(title="Variant")
    locus: Optional[LocusContext] = Field(default=None, title="Locus")

    # variant_evidence: Optional[List[GenePrioritizationAnnotation]] = Field(
    #     default=None,
    #     title="Variant Evidence",
    # )
    # gene_evidence: Optional[List[GenePrioritizationAnnotation]] = Field(
    #     default=None,
    #     title="Gene Evidence",
    # )
    # integration: Optional[List[GenePrioritizationAnnotation]] = Field(
    #     default=None,
    #     title="Integration Evidence",
    #     description="Combined evidence supporting prioritization of this gene",
    # )
