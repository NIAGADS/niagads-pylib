from typing import List

from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.parameters.response import ResponseView


class Collection(RowModel):
    name: str
    description: str
    num_tracks: int

    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()


class CollectionResponse(GenericResponse):
    data: List[Collection]
