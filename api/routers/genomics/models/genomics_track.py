from typing import List, Optional

from pydantic import BaseModel

from api.common.enums import ResponseView
from api.models.base_models import RowModel
from api.models.base_response_models import PagedResponseModel
from api.models.biosample_characteristics import BiosampleCharacteristics
from api.models.provenance import Provenance
from api.models.track import ExtendedGenericTrack, GenericTrack
from api.routers.genomics.common.constants import Covariate
from api.routers.genomics.models.phenotype import Phenotype

# NOTE: 'Track Brief' is just the GenericTrack

class GroupCounts(BaseModel):
    group: str
    count: int

class GenomicsTrack(ExtendedGenericTrack):
    description: str
    attribtution: Optional[str] # FIXME: publication? pubmed id?
    accession: str
    collections: Optional[List[str]]
    cohorts: Optional[List[str]]
    subject_summary: List[GroupCounts] # FIXME: name? {cases: N, controls: N}
    phenotypes: Phenotype
    covariates: List[Covariate]
    

class GenomicsTrackBriefResponse(PagedResponseModel):
    response: List[GenericTrack]
    
    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)

    
class GenomicsTrackResponse(PagedResponseModel):
    response: List[GenomicsTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)