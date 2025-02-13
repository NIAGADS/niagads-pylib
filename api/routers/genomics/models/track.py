from typing import List

from api.models.base_models import RowModel
from api.models.base_response_models import PagedResponseModel
from api.models.biosample_characteristics import BiosampleCharacteristics
from api.models.provenance import Provenance
from api.models.track import GenericTrack

class Track(GenericTrack):
    track_id: str
    name: str
    description: str
    attribtution: str # FIXME: publication? pubmed id?
    accession: str
    collections: List[str]
    url: str
    data_source: str
    data_type: str
    

    
    # TODO biosample, provenance, etc
    biosample_characteristics: BiosampleCharacteristics
    provenance: Provenance
    
class TrackResponse(PagedResponseModel):
    response: List[Track]