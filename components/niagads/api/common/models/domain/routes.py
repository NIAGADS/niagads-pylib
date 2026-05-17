from typing import List, Optional, Set


from niagads.api.common.models.service.entity_search import EntityRecordStats
from pydantic import Field
from niagads.common.models.base import CustomBaseModel
from niagads.common.types import T_PubMedID


class RouteDescriptor(CustomBaseModel):
    name: str = Field(..., description="Route name.")
    description: str = Field(..., description="Short description of the route.")
    publications: Optional[Set[T_PubMedID]] = Field(
        None, description="Set of PubMed IDs for supporting publications."
    )
    url: str = Field(..., description="URL for the route.")
    records: List[EntityRecordStats] = Field(
        ..., description="List of entity record statistics for this route."
    )
