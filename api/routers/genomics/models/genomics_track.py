from typing import List, Optional

from pydantic import BaseModel

from api.common.enums.response_properties import ResponseView

from api.models.base_response_models import PagedResponseModel
from api.models.track import GenericTrack, GenericTrackSummary
from api.models.track_properties import DSSAccession
from api.routers.genomics.common.constants import Covariate
from api.routers.genomics.models.phenotype import Phenotype

class StudyGroup(BaseModel):
    group: str
    count: int

class GenomicsTrack(GenericTrack):
    description: str
    provenance: DSSAccession
    
class HumanGenomicsTrack(GenomicsTrack):
    cohorts: Optional[List[str]] = None
    study_groups: List[StudyGroup] 
    phenotypes: Optional[Phenotype] = None
    covariates: List[Covariate]
    
class GenomicsTrackSummaryResponse(PagedResponseModel):
    response: List[GenericTrackSummary]
    
    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)

    
class GenomicsTrackResponse(PagedResponseModel):
    response: List[GenomicsTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)