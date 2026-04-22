"""
Pydantic models for gene annotations
"""

from typing import ClassVar
from niagads.common.models.annotations import (
    AnnotationEvidenceMixin,
    AnnotationType,
    ScoreMixin,
)
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.reference.xrefs.models import Pathway
from pydantic import Field


class GOAssociation(AnnotationEvidenceMixin, OntologyTerm):
    """
    Represents a Gene Ontology (GO) association annotation for a gene
    """

    annotation_type: ClassVar[AnnotationType] = AnnotationType.KNOW


class PathwayMembership(AnnotationEvidenceMixin, Pathway):
    """
    Represents a pathway membership annotation for a gene
    """

    annotation_type: ClassVar[AnnotationType] = AnnotationType.SET

    def __str__(self):
        """Return the pathway name as string representation."""
        return self.pathway_name
