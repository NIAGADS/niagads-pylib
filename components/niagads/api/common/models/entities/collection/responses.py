from typing import List

from niagads.api.common.models.entities.collection.records import CollectionMetadata
from niagads.api.common.models.responses.data import DataResponse
from pydantic import Field


class TrackCollectionResponse(DataResponse):
    data: List[CollectionMetadata] = Field(
        description="List of track collections meeting the query criteria."
    )
