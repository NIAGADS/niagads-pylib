"""
Pydantic models for composite attributes related to gene features
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GOEvidence(BaseModel):
    """
    Represents evidence supporting a Gene Ontology (GO) annotation.

    Attributes:
        citation (Optional[str]): PMID or GO Reference used by the GO consortium.
        qualifier (Optional[str]): Context for interpreting the GO annotation.
        evidence_code (Optional[str]): ECO term ID from the Evidence and Conclusion Ontology.
        go_evidence_code (Optional[str]): GO Evidence Code.
        annotation_source (Optional[str]): Source of the annotation (annotator).
        evidence_code_qualifier (Optional[str]): Qualifier for the evidence code (usually the gene, excluded).
    """

    citation: Optional[str] = Field(
        default=None,
        title="Citation",
        description="PMID or GO Reference (non-PMID) used by the GO consortium.  See https://geneontology.org/gorefs.html.",
        examples=["GO_REF:0000024"],
    )
    qualifier: Optional[str] = Field(
        default=None,
        title="Qualifier",
        description="context for interpreting the GO annotation",
        examples=["involved_in"],
    )
    evidence_code: Optional[str] = Field(
        default=None,
        title="ECO ID",
        description="term id in the Evidence and Conclusion Ontology.  See https://www.evidenceontology.org/.",
        examples=["ECO:0000250"],
    )  # ontology_term_id
    go_evidence_code: Optional[str] = Field(
        default=None,
        title="Evidence Code",
        description="GO Evidence Code. See https://geneontology.org/docs/guide-go-evidence-codes/.",
    )  # code
    annotation_source: Optional[str] = Field(
        default=None, title="Annotation Source", description="annotator"
    )

    # excluding this b/c it is (usually) the gene
    evidence_code_qualifier: Optional[str] = Field(
        default=None, title="Evidence Code Qualifier", exclude=True
    )

    def __str__(self):
        """Return the GO evidence code as string representation."""
        return self.go_evidence_code


class GOAnnotation(BaseModel):
    """
    Represents a Gene Ontology (GO) annotation for a gene or feature.

    Attributes:
        go_term_id (str): GO Term ID.
        go_term (str): the GO term.
        ontology (str): Ontology type (e.g., biological process, molecular function).
        evidence (List[GOEvidence]): List of supporting evidence codes.
    """

    go_term_id: str = Field(title="GO Term ID")
    go_term: str = Field(title="Term")
    ontology: str = Field(title="Ontology")
    evidence: List[GOEvidence] = Field(
        title="Evidence Code",
        description="GO Evidence Code. See https://geneontology.org/docs/guide-go-evidence-codes/.",
    )


class PathwayAnnotation(BaseModel):
    """
    Represents a pathway annotation for a gene or feature.

    Attributes:
        pathway (str): Name of the pathway.
        pathway_id (str): Identifier for the pathway.
        pathway_source (str): Data source for the pathway annotation.
    """

    pathway: str = Field(title="Pathway")
    pathway_id: str = Field(title="Pathway ID")
    pathway_source: str = Field(
        title="Source", description="data source for the pathway annotation"
    )
    evidence_code: Optional[str] = Field(default=None, title="GO Evidence Code")

    def __str__(self):
        """Return the pathway name as string representation."""
        return self.pathway
