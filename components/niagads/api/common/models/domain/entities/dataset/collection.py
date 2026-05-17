from typing import List


from niagads.api.common.models.domain.mixins import ORMCompatabileMixin
from niagads.common.models.base import CustomBaseModel
from pydantic import Field


class Collection(CustomBaseModel, ORMCompatabileMixin):
    id: str = Field(
        title="Collection ID",
        description="Unique collection identifier; may be a NIAGADS Dataset Accession",
    )
    name: str = Field(title="Name")
    description: str = Field(title="Description")
    num_tracks: int = Field(
        title="Number of Tracks", description="number of data tracks in the collection"
    )


class CollectionResponse(ResponseModel):
    data: List[Collection]
