from typing import Dict, List, Optional, Union

from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.records.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.response.core import GenericResponse
from pydantic import BaseModel, ConfigDict, Field


class GeneFeature(RowModel):
    id: str
    gene_symbol: Optional[str] = Field(default=None, serialization_alias="symbol")

    # should allow to fill from SQLAlchemy ORM model
    # model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class Gene(GeneFeature):
    gene_type: Optional[str] = Field(default=None, serialization_alias="type")
    gene_name: Optional[str] = Field(default=None, serialization_alias="name")
    synonyms: Optional[List[str]] = None
    location: GenomicRegion


class GOEvidence(BaseModel):
    citation: Optional[str] = None
    qualifier: Optional[str] = None
    evidence_code: Optional[str] = None
    go_evidence_code: Optional[str] = None
    annotation_source: Optional[str] = None
    evidence_code_qualifier: Optional[str] = None


class GOAnnotation(BaseModel):
    go_term_id: str
    go_term: str
    ontology: str
    evidence: List[GOEvidence]


class PathwayAnnotation(BaseModel):
    pathway: str
    pathway_id: str
    pathway_source: str


class AnnotatedGene(Gene):
    hgnc_annotation: Optional[Dict[str, Union[str, int]]] = None
    go_annotation: Optional[List[GOAnnotation]] = None
    pathway_membership: Optional[List[PathwayAnnotation]] = None
    # rifs: Optional[dict] = None


class AbridgedGeneResponse(GenericResponse):
    data: List[Gene]


class GeneResponse(GenericResponse):
    data: List[AnnotatedGene]
