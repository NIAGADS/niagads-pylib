from typing import List, Optional
from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.types import PrimitiveType
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import dict_to_info_string, matches
from pydantic import ConfigDict, Field, model_validator


# TODO: map to "ontologies"
class AnnotationType(CaseInsensitiveEnum):
    """
    adapted from Predicted Effector Genes (PEG) Aggregation, Standards, and Unified Schema (PEGASUS) framework
    https://ebispot.github.io/PEGASUS/docs/peg-overview

    LD = Linkage disequilibrium
    FM = Finemapping and credible sets
    COLOC = Colocalisation
    QTL = Molecular QTL
    MR = Mendelian Randomization
    REG = Regulatory region
    CHROMATIN = Chromatin interaction
    FUNC = Predicted functional impact
    PROX = Proximity to gene
    GWAS = Genome-wide association signal
    PHEWAS = PheWAS
    PPI = Protein-protein interaction
    SET = Pathway or gene sets
    GENEBASE = Gene-based association
    EXP = Expression
    PERTURB = Perturbation
    KNOW = Biological Knowledge Inference
    TPWAS = Genetically predicted trait association
    DRUG = Drug related
    CROSSP = Cross-phenotype
    LIT = Literature curation
    DB = Association from curated database
    INT = Integrated evidence
    """

    LD = "Linkage disequilibrium"  # mesh:D015810 # EDAM:operation_0488
    FM = "Finemapping and credible sets"  # EDAM:operation_0282
    COLOC = "Colocalisation"
    QTL = "Molecular QTL"
    MR = "Mendelian Randomization"
    REG = "Regulatory region"
    CHROMATIN = "Chromatin interaction"
    FUNC = "Predicted functional impact"
    PROX = "Proximity to gene"
    GWAS = "Genome-wide association signal"
    PHEWAS = "PheWAS"
    PPI = "Protein-protein interaction"
    SET = "Pathway or gene sets"
    GENEBASE = "Gene-based association"
    EXP = "Expression"
    PERTURB = "Perturbation"
    KNOW = "Biological Knowledge Inference"
    TPWAS = "Genetically predicted trait association"
    DRUG = "Drug related"
    CROSSP = "Cross-phenotype"
    LIT = "Literature curation"
    DB = "Association from curated database"
    INT = "Integrated evidence"


class AnnotationEvidenceQualifier(CustomBaseModel):
    reference_accession: Optional[str] = Field(
        default=None,
        description="database or literature reference",
    )
    description: Optional[str] = Field(
        default=None,
        title="Additional descriptive, qualifying information about the evidence",
    )
    data_source: Optional[str] = Field(
        default=None, description="source database for the reference_accession"
    )

    # additional, project specific qualifiers
    # e.g., GAF WithOrFrom, 'qualifier'
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_data_source_required(self):
        """
        Validate that data_source is required if reference_accession is not a PubMed ID.
        """
        if not self.data_source and self.reference_accession:
            if not matches(RegularExpressions.PUBMED_ID, self.reference_accession):

                raise ValueError(
                    "data_source is required when reference_accession is not a PubMed ID"
                )
        return self

    def __str__(self):
        return dict_to_info_string(
            self.model_dump(exclude_none=True, exclude_unset=True)
        )


class AnnotationEvidenceDescriptor(CustomBaseModel):
    """
    Represents evidence supporting a Gene Ontology (GO) annotation.
    """

    qualifiers: Optional[AnnotationEvidenceQualifier] = Field(
        default=None,
        title="Qualifiers",
        description="context for interpreting the GO annotation, includes GO References and citations",
    )
    evidence_code: OntologyTerm = Field(
        title="Evidence Code",
        description="term in the Evidence and Conclusion Ontology (ECO).  See https://www.evidenceontology.org/.",
    )

    def __str__(self):
        """Return the GO evidence code as string representation."""
        return self.evidence_code.term

    def __str__(self):

        if self.qualifiers:
            return f"{self.evidence_code};{str(self.qualifiers)}"
        return self.evidence_code.term

    def __hash__(self):  # so that we can generate unique sets of evidence
        return hash(str(self))


class AnnotationEvidenceMixin:
    annotation_type: AnnotationType = Field(
        title="Annotation Type",
        description="type of annotation; adapted from Predicted Effector Genes (PEG) Aggregation, Standards, and Unified Schema framework",
    )
    evidence: List[AnnotationEvidenceDescriptor] = Field(
        title="Evidence",
        description="evidence for this gene-go-association",
    )


class ScoreMixin:
    metric: Optional[OntologyTerm] = Field(
        default=None, title="Scoring or labeling metric"
    )
    value: Optional[PrimitiveType] = Field(default=None, title="Value")
