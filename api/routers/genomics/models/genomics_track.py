from typing import List, Optional

from pydantic import BaseModel

from api.common.enums import ResponseView
from api.models.base_models import RowModel
from api.models.base_response_models import PagedResponseModel
from api.models.biosample_characteristics import BiosampleCharacteristics
from api.models.provenance import DSSAccession, Provenance
from api.models.track import DetailedGenericTrack, GenericTrack
from api.routers.genomics.common.constants import Covariate
from api.routers.genomics.models.phenotype import Phenotype

# NOTE: 'Track Brief' is just the GenericTrack


class StudyGroup(BaseModel):
    group: str
    count: int

class GenomicsTrack(DetailedGenericTrack):
    description: str
    provenance: DSSAccession
    
class HumanGenomicsTrack(GenomicsTrack):
    cohorts: Optional[List[str]]
    study_groups: List[StudyGroup] 
    phenotypes: Optional[Phenotype]
    covariates: List[Covariate]
    
class GenomicsTrackSummaryResponse(PagedResponseModel):
    response: List[GenericTrack]
    
    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)

    
class GenomicsTrackResponse(PagedResponseModel):
    response: List[GenomicsTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)