from typing import List, Union

from niagads.api.common.models.entities.track.records import (
    TrackMetadata,
    TrackMetadataBrief,
)
from niagads.api.common.models.responses.data import DataResponse
from pydantic import Field


class TrackMetadataResponse(DataResponse):

    data: List[Union[TrackMetadataBrief, TrackMetadata]] = Field(
        description="Metadata (optionally brief) for each track meeting the query criteria."
    )
