from typing import List

from niagads.api.common.models.domain.entities.features.bed import BEDFeature
from niagads.api.common.services.pagination import (
    TrackDataPaginationCursor,
    TrackDataPaginationService,
)
from niagads.filer_service.api.services.wrapper import FILERApiDataResponse


class FILERTrackDataPaginationService(TrackDataPaginationService):

    def page_data(
        self, cursor: TrackDataPaginationCursor, data: List[FILERApiDataResponse]
    ) -> List[BEDFeature]:

        # sort the response by the cursor pagedTracks so the track order is correct
        # FILER currently processes sequentially so this is unecessary but if updated
        # to process in parallel, it will be required
        sortedData = sorted(data, key=lambda x: cursor.tracks == x.Identifier)

        result: List[BEDFeature] = []
        for trackIndex, track in enumerate(sortedData):
            sliceStart = cursor.start.offset if trackIndex == cursor.start.key else None
            sliceEnd = cursor.end.offset if trackIndex == cursor.end.key else None

            features: List[BEDFeature] = track.features[sliceStart:sliceEnd]
            for f in features:
                f.add_track(track.Identifier)
                result.append(f)

        return result
