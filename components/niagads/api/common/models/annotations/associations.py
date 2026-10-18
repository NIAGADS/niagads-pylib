from typing import Optional

from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.genome_reference.human import HumanGenome
from pydantic import Field

from niagads.api.common.models.records.types import ORMCompatibleRecord


class VariantAssociation(ORMCompatibleRecord):
    id: str = Field(
        default=None,
        title="Variant ID",
        description="stable identifier for the variant associated with the result",
    )
    chromosome: HumanGenome = Field(..., title="Chromosome")
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
        default=None,
        title="Negative Log10 p-value",
        description="negative base-10 logarithm of the association p-value",
    )
    pvalue: str = Field(
        default=None,
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
    traits: Optional[dict[str, list[OntologyTerm]]] = Field(
        ...,
        title="Traits",
        description="associated phenotypic traits classified by context",
    )
