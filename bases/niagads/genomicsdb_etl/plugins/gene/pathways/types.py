from typing import Optional
from pydantic import BaseModel, Field


class PathwayInfo(BaseModel):
    pathway_id: str
    pathway_name: str


class MembershipAnnotation(BaseModel):
    gene_id: str
    evidence_code: Optional[str] = None


# FIXME: note that for reactome, you will need a transform now
# to transform the dict extracted from the table into this data structure
# EGA thinks that in reactome, the list size for each will be 1
# get_record_id probably needs to be done differently for each KEGG will log a "pathway", while REACTOME will log a pathway:gene


class PathwayGeneAssociations(BaseModel):
    """Model for pathway annotation."""

    pathway_info: PathwayInfo
    member_genes: list[MembershipAnnotation]

    model_config = {"extra": "ignore"}
