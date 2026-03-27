from pydantic import BaseModel, Field

class PathwayAnnotation(BaseModel):
    id: str = Field(alias="gene_id")
    pathway_id: str
    pathway_name: str
    pathway_url: str
    evidence_code: str
    

    model_config = {"extra": "ignore"}