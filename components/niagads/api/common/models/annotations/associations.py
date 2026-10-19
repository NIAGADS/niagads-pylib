from typing import Optional

from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.genome_reference.human import HumanGenome
from pydantic import Field

from niagads.api.common.models.records.types import ORMCompatibleRecord


class VariantAssociation(ORMCompatibleRecord):
    variant: str = Field(
        ...,
        title="Variant ID",
        description="stable identifier for the variant associated with the result",
    )
    chromosome: HumanGenome = Field(..., title="Chromosome")
    position: int = Field(..., title="Position (BP)")
    ref: str = Field(
        default=None,
        title="Reference Allele",
        description="reference allele sequence",
    )
    alt: str = Field(
        default=None,
        title="Alternate Allele",
        description="alternate allele sequence",
    )

    neg_log10_pvalue: float = Field(
        ...,
        title="Negative Log10 p-value",
        description="negative base-10 logarithm of the association p-value",
    )
    pvalue: str = Field(
        ...,
        title="p-value",
        description="association p-value reported for the variant",
    )
    effect_direction: str = Field(
        default=None,
        title="Effect Direction",
        description="direction of the observed effect for the variant association",
    )
    test_allele: Optional[str] = Field(
        default=None,
        title="Test Allele",
        description="allele used to evaluate the association",
    )
    traits: dict[str, list[OntologyTerm]] = Field(
        ...,
        title="Traits",
        description="associated phenotypic traits classified by context",
    )
    track: Optional[str] = Field(
        ...,
        title="Track ID",
        description="identifier for the source data track for the association",
    )
