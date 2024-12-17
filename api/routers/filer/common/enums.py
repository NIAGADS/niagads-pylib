from api.common.enums import CaseInsensitiveEnum, ResponseContent
from api.dependencies.parameters.optional import get_response_content

class FILERApiEndpoint(CaseInsensitiveEnum):
    OVERLAPS = 'get_overlaps'
    INFORMATIVE_TRACKS = 'get_overlapping_tracks_by_coord'
    METADATA = 'get_metadata'
    
    def __str__(self):
        return f"{self.name}.php"
    
METADATA_CONTENT_ENUM = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.COUNTS])
TRACK_DATA_CONTENT_ENUM = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.SUMMARY])
