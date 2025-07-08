from typing import List, Optional
from pydantic import BaseModel, Field


class GOEvidence(BaseModel):
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
        return self.go_evidence_code


class GOAnnotation(BaseModel):
    go_term_id: str = Field(title="GO Term ID")
    go_term: str = Field(title="Term")
    ontology: str = Field(title="Ontology")
    evidence: List[GOEvidence] = Field(
        title="Evidence Code",
        description="GO Evidence Code. See https://geneontology.org/docs/guide-go-evidence-codes/.",
    )


class PathwayAnnotation(BaseModel):
    pathway: str = Field(title="Pathway")
    pathway_id: str = Field(title="Pathway ID")
    pathway_source: str = Field(
        title="Source", description="data source for the pathway annotation"
    )

    def __str__(self):
        return self.pathway
