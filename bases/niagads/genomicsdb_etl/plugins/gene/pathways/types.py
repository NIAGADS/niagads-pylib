from typing import Optional
from pydantic import BaseModel, Field


class GenePathwayAssociation(BaseModel):
    """Model for KEGG pathway annotation."""

    gene_id: str = Field(alias="id")
    pathway_id: str
    pathway_name: str
    evidence_code: str

    model_config = {"extra": "ignore"}
