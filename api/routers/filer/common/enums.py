from api.common.enums import CaseInsensitiveEnum

class FILERApiEndpoint(CaseInsensitiveEnum):
    OVERLAPS = 'get_overlaps'
    INFORMATIVE_TRACKS = 'get_overlapping_tracks_by_coord'
    METADATA = 'get_metadata'
    
    def __str__(self):
        return f"{self.name}.php"