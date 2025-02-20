from typing import List, Optional


from api.common.enums.response_properties import ResponseView

from api.models.base_response_models import PagedResponseModel
from api.models.track import GenericTrack, GenericTrackSummary
from api.models.track_properties import DSSAccession
from api.routers.genomics.models.genomics_track_properties import Phenotype, StudyGroup

class GenomicsTrack(GenericTrack):
    description: str
    provenance: DSSAccession
    cohorts: Optional[List[str]] = None
    study_groups: Optional[List[StudyGroup]] = None
    phenotypes: Optional[Phenotype] = None
    covariates: Optional[str] = None
    
class GenomicsTrackSummaryResponse(PagedResponseModel):
    response: List[GenericTrackSummary]
    
    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names() \
            if len(self.response) > 0 else GenericTrackSummary.get_model_fields()
        return super().to_text(format, fields=fields)

    
class GenomicsTrackResponse(PagedResponseModel):
    response: List[GenomicsTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = GenomicsTrack.get_model_fields()
        return super().to_text(format, fields=fields)