from typing import Optional
from pydantic import BaseModel, Field


class GenePathwayAssociation(BaseModel):
    """Model for KEGG pathway annotation."""

    gene_id: str
    pathway_id: str
    pathway_name: str
    evidence_code: Optional[str] = None

    model_config = {"extra": "ignore"}
