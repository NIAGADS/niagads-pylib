from api.common.enums.base_enums import CaseInsensitiveEnum

class FILERApiEndpoint(CaseInsensitiveEnum):
    OVERLAPS = 'get_overlaps'
    INFORMATIVE_TRACKS = 'get_overlapping_tracks_by_coord'
    METADATA = 'get_metadata'
    
    def __str__(self):
        return f"{self.value}.php"
    
# METADATA_FORMAT_ENUM = get_response_format(exclude=[ResponseFormat.BED, ResponseFormat.VCF])
# METADATA_CONTENT_ENUM = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.COUNTS, ResponseContent.URLS])

# TRACK_DATA_CONTENT_ENUM = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.SUMMARY, ResponseContent.URLS])
