from typing import Dict, List, Optional, Union

from niagads.common.models.core import TransformableModel
from niagads.open_access_api_common.models.core import RowModel
from niagads.open_access_api_common.models.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.response.core import RecordResponse
from pydantic import BaseModel, Field


class GeneFeature(RowModel):
    id: str = Field(title="Ensembl ID", description="Ensembl gene identifier")
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
        serialization_alias="symbol",
    )

    def __str__(self):
        return self.id

    # should allow to fill from SQLAlchemy ORM model
    # model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class Gene(GeneFeature):
    gene_type: Optional[str] = Field(default=None, serialization_alias="type")
    gene_name: Optional[str] = Field(default=None, serialization_alias="name")
    synonyms: Optional[List[str]] = Field(
        default=None, title="Aliases", descriptions="gene symbol synonyms or aliases"
    )
    location: GenomicRegion = Field(
        title="Location",
        description="genomic location delimiting the footprint (span) of the gene",
    )

    def __str__(self):
        return self.as_info_string()

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)
        if self.synonyms is not None:
            obj["synonyms"] = self._list_to_string(self.synonyms, delimiter=delimiter)

        # promote the location fields
        del obj["location"]
        obj.update(self.location._flat_dump())
        return obj

    @classmethod
    def get_model_fields(cls, asStr=False):
        fields = super().get_model_fields()
        del fields["location"]
        fields.update(GenomicRegion.get_model_fields())

        return list(fields.keys()) if asStr else fields


class GOEvidence(TransformableModel):
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


class GOAnnotation(TransformableModel):
    go_term_id: str
    go_term: str
    ontology: str
    evidence: List[GOEvidence]

    def __str__(self):
        return self.as_info_string()

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)
        if self.evidence is not None:
            obj["evidence"] = self._list_to_string(self.evidence, delimiter=delimiter)
        return obj


class PathwayAnnotation(TransformableModel):
    pathway: str
    pathway_id: str
    pathway_source: str

    def __str__(self):
        return self.as_info_string()


class AnnotatedGene(Gene):
    hgnc_annotation: Optional[Dict[str, Union[str, int]]] = None
    go_annotation: Optional[List[GOAnnotation]] = None
    pathway_membership: Optional[List[PathwayAnnotation]] = None

    def as_info_string(self):
        raise NotImplementedError("Not implemented for Annotated Genes")

    def as_list(self, fields=None):
        raise NotImplementedError("Not implemented for Annotated Genes")

    def as_table_row(self, **kwargs):
        raise NotImplementedError("Not implemented for Annotated Genes")


class AbridgedGeneResponse(RecordResponse):
    data: List[Gene]


class GeneResponse(RecordResponse):
    data: List[AnnotatedGene]

    def to_table(self, id=None, title=None):
        raise NotImplementedError("Table views not avaialble for `FULL` gene records.")

    def to_text(self, inclHeader=False, nullStr=None):
        raise NotImplementedError(
            "Plain text responses not available for `FULL` gene records."
        )
