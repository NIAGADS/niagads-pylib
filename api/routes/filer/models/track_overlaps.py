from typing import List
from api.common.enums.response_properties import ResponseFormat, ResponseView
from api.models.base_row_models import RowModel

class TrackOverlap(RowModel):
    track_id: str
    num_overlaps: int
    
    def get_view_config(self, view: ResponseView, **kwargs):
        raise RuntimeError('View transformations not implemented for this row model.')
    
    def to_view_data(self, view: ResponseView, **kwargs):
        raise RuntimeError('View transformations not implemented for this row model.')
    
    def to_text(self, format: ResponseFormat, **kwargs):
        return f'{self.track_id}\t{self.num_overlaps}'
    

def sort_track_overlaps(trackOverlaps: List[TrackOverlap], reverse=True) -> List[TrackOverlap]:
    return sorted(trackOverlaps, key = lambda item: item.num_overlaps, reverse=reverse)    