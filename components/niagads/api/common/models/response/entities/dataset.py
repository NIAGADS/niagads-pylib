from typing import List, Union

from niagads.api.common.models.domain.entities.dataset.collection import (
    CollectionMetadata,
)
from niagads.api.common.models.domain.entities.dataset.track import (
    TrackMetadata,
    TrackMetadataBrief,
)
from niagads.api.common.models.response.base import StandardDataSerializationResponse
from pydantic import Field


class TrackMetadataResponse(StandardDataSerializationResponse):

    data: List[Union[TrackMetadataBrief, TrackMetadata]] = Field(
        description="Metadata (optionally brief) for each track meeting the query criteria."
    )


class CollectionMetadataResponse(StandardDataSerializationResponse):
    data: List[CollectionMetadata] = Field(
        description="List of track collections meeting the query criteria."
    )
