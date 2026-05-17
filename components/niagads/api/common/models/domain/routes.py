from typing import List, Optional, Set


from pydantic import Field
from niagads.api.common.models.entities import EntityRecordStats
from niagads.common.models.base import CustomBaseModel
from niagads.common.types import T_PubMedID


class RouteDescription(CustomBaseModel):
    name: str = Field(..., description="Route name.")
    description: str = Field(..., description="Short description of the route.")
    publications: Optional[Set[T_PubMedID]] = Field(
        None, description="Set of PubMed IDs for supporting publications."
    )
    url: str = Field(..., description="URL for the route.")
    records: List[EntityRecordStats] = Field(
        ..., description="List of entity record statistics for this route."
    )
