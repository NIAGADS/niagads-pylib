from pydantic import BaseModel, Field

class PathwayAnnotation(BaseModel):
    gene_id: str
    pathway_id: str
    pathway_name: str
    pathway_url: str
    evidence_code: str
    species: str

    model_config = {"extra": "ignore"}