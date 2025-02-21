import json
from typing import List, Optional


from api.common.enums.response_properties import ResponseView

from api.models.base_response_models import PagedResponseModel
from api.models.track import GenericTrack, GenericTrackSummary
from api.models.track_properties import DSSAccession
from api.models.view_models import TextDataCell, TextListDataCell
from api.routers.genomics.models.genomics_track_properties import Phenotype, StudyGroup

class GenomicsTrack(GenericTrack):
    description: str
    provenance: DSSAccession
    cohorts: Optional[List[str]] = None
    study_groups: Optional[List[StudyGroup]] = None
    phenotypes: Optional[Phenotype] = None
    covariates: Optional[str] = None
    
    def to_view_data(self, view: ResponseView, **kwargs):
        data = super().to_view_data(view, promoteObjs=True)
        # FIXME: handle dictonary cell types on table side of things
        if 'study_groups' in data and data['study_groups'] is not None:
            data['study_groups'] = json.dumps(data['study_groups'])
            
        # FIXME: getting Input should be a subclass of DataCell [type=is_subclass_of, input_value=TextListDataCell(type=('t...'black', tooltip=None)]), input_type=TextListDataCell]\n 
        # even though TextListDataCell is a subtype of DataCell
        if 'cohorts' in data and data['cohorts'] is not None:
            data['cohorts'] = ' // '.join(data['cohorts'])
            # data['cohorts'] = TextListDataCell(items=[TextDataCell(value=c) for c in data['cohorts']])
        return data
    
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