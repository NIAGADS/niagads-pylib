from typing import List, Union

from niagads.api.common.models.domain.entities.dataset.track import (
    TrackMetadata,
    TrackMetadataBrief,
)
from niagads.api.common.models.response.base import BaseResponseModel
from pydantic import Field


class TrackMetadataResponse(BaseResponseModel):

    data: List[Union[TrackMetadataBrief, TrackMetadata]] = Field(
        description="Metadata (optionally brief) for each track meeting the query criteria "
    )
