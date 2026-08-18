from typing import List, Optional, Set

from niagads.api.common.types import Entity
from niagads.common.models.base import CustomBaseModel
from niagads.common.types import T_PubMedID
from pydantic import Field


class EntityMetrics(CustomBaseModel):
    entity: Entity
    num_records: int


class RouteDescriptor(CustomBaseModel):
    name: str = Field(..., description="Route name.")
    description: str = Field(..., description="Short description of the route.")
    publications: Optional[Set[T_PubMedID]] = Field(
        None, description="Set of PubMed IDs for supporting publications."
    )
    url: str = Field(..., description="URL for the route.")
    records: List[EntityMetrics] = Field(
        ..., description="List of entity record statistics for this route."
    )
