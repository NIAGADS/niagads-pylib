"""
Pydantic models for gene annotations
"""

from typing import List, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.common.ontologies.models import OntologyTerm
from niagads.common.reference.xrefs.models import Pathway
from pydantic import Field


class GeneAnnotationEvidence(CustomBaseModel):
    """
    Represents evidence supporting a Gene Ontology (GO) annotation.
    """

    qualifier: Optional[dict] = Field(
        default=None,
        title="Qualifier",
        description="context for interpreting the GO annotation, includes GO References and citations",
    )
    evidence_code: OntologyTerm = Field(
        title="Evidence Code",
        description="term in the Evidence and Conclusion Ontology (ECO).  See https://www.evidenceontology.org/.",
    )

    def __str__(self):
        """Return the GO evidence code as string representation."""
        return self.evidence_code.term


class GOAssociation(CustomBaseModel):
    """
    Represents a Gene Ontology (GO) association annotation for a gene
    """

    term: OntologyTerm = Field(title="GO Term", description="Gene Ontology (GO) Term")
    ontology: str = Field(title="Ontology", description="Gene Ontology")
    evidence: List[GeneAnnotationEvidence] = Field(
        title="Evidence",
        description="evidence for this gene-go-association",
    )


class PathwayMembership(CustomBaseModel):
    """
    Represents a pathway membership annotation for a gene
    """

    pathway: Pathway = Field(title="Pathway")
    evidence: Optional[List[GeneAnnotationEvidence]] = Field(
        default=None,
        title="Evidence",
        description="evidence for this pathway membership",
    )

    def __str__(self):
        """Return the pathway name as string representation."""
        return self.pathway
