"""
Pydantic models for gene annotations
"""

from niagads.common.models.annotation import AnnotationType, BaseAnnotation
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.reference.xrefs.models import Pathway
from pydantic import Field


class GOAssociation(BaseAnnotation):
    """
    Represents a Gene Ontology (GO) association annotation for a gene
    """

    annotation_type = AnnotationType.KNOW
    term: OntologyTerm = Field(title="GO Term", description="Gene Ontology (GO) Term")
    namespace: str = Field(
        title="Namespace", description="Gene Ontology (GO) namespace"
    )


class PathwayMembership(BaseAnnotation):
    """
    Represents a pathway membership annotation for a gene
    """

    annotation_type = AnnotationType.SET
    pathway: Pathway = Field(title="Pathway")

    def __str__(self):
        """Return the pathway name as string representation."""
        return self.pathway
