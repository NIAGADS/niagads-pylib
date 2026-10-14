from typing import Any, Dict, List, Optional

from niagads.common.genomic.regions.models import GenomicRegion
from niagads.common.models.base import CustomBaseModel
from pydantic import Field


class GeneIdentifier(CustomBaseModel):
    id: str = Field(title="Ensembl ID", description="Ensembl gene identifier")
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
        serialization_alias="symbol",
    )
    location: Optional[GenomicRegion] = Field(
        default=None,
        title="Location",
        description="genomic location delimiting the footprint (span) of the gene",
    )

    def __str__(self):
        return self.id


class GeneRecord(GeneIdentifier):
    gene_type: Optional[str] = Field(
        default=None,
        title="Gene Type",
        description="biological type or classification of the gene",
    )
    nomenclature: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Nomenclature",
        description="gene naming information, including the symbol, name, and synonyms",
    )
    gene_structure: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Gene Structure",
        description="gene location, cytogenetic location, and transcript structure",
    )
    xrefs: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Cross References",
        description="cross-references to external gene identifiers and resources",
    )
    publications: Optional[List[Any]] = Field(
        default=None,
        title="Publications",
        description="publications associated with the gene",
    )
    memberships: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Memberships",
        description="gene memberships in families, pathways, and curated lists",
    )
    functional_annotation: Optional[List[Any]] = Field(
        default=None,
        title="Functional Annotation",
        description="functional annotations associated with the gene",
    )
    associated_with_known_ad_locus: Optional[bool] = Field(
        default=None,
        title="Associated with Known AD Locus",
        description=(
            "indicates whether the gene is associated with a known "
            "Alzheimer’s disease locus"
        ),
    )

    def __str__(self):
        return self.id
