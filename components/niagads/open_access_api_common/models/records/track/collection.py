from typing import List

from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.parameters.response import ResponseView
from pydantic import Field


class Collection(RowModel):
    primary_key: str = Field(
        serialization_alias="id",
        title="Collection ID",
        description="Unique collection identifier; may be a NIAGADS Dataset Accession",
    )
    name: str = Field(title="Name")
    description: str = Field(title="Description")
    num_tracks: int = Field(
        title="Number of Tracks", description="number of data tracks in the collection"
    )

    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()


class CollectionResponse(GenericResponse):
    data: List[Collection]
