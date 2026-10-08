"""
Pydantic models for gene annotations
 - note these do not include external_database references by design
 - those will depend on application  (e.g., table for database, response model for API)
    which will bring distributed information back together
"""

from typing import ClassVar, Optional
from niagads.common.models.annotations import (
    AnnotationEvidenceMixin,
    AnnotationType,
    ScoreMixin,
)
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.reference.xrefs.models import Pathway


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


class OpenTargetAssociation(AnnotationEvidenceMixin, ScoreMixin):
    disease: OntologyTerm
    target: OntologyTerm

    data_type: OntologyTerm  # aggregation type
    data_source: Optional[str] = None  # or does this go into qualifier->reference
    # max evidence_count a qualifier?

    # Set evidence code to ECO_0007669 / computational evidence used in automatic assertion
    # in plugin


# overall

# disease Id
# target Id
# aggregationType
# aggregationValue - may not be relevant
# association score
# evidence count (float)
#

# aggregationtype / #aggregation value
# may be: direct -> by data type
#   -- datatype id / datasource id
# may be: direct -> by data source
#    -- data source id / group e.g., gwas_credible_scores
