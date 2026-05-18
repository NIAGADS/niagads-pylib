from typing import List, Union

from niagads.api.common.models.domain.entities.dataset.collection import (
    CollectionMetadata,
)
from niagads.api.common.models.domain.entities.dataset.track import (
    TrackMetadata,
    TrackMetadataBrief,
)
from niagads.api.common.models.response.base import DataResponse
from pydantic import Field


class TrackMetadataResponse(DataResponse):

    data: List[Union[TrackMetadataBrief, TrackMetadata]] = Field(
        description="Metadata (optionally brief) for each track meeting the query criteria."
    )


class CollectionMetadataResponse(DataResponse):
    data: List[CollectionMetadata] = Field(
        description="List of track collections meeting the query criteria."
    )
