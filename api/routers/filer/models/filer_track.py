from sqlmodel import SQLModel
from typing import Any, Dict, Optional, List, Union
from typing_extensions import Self
from pydantic import model_validator

from niagads.utils.list import find

from api.common.constants import JSON_TYPE
from api.common.enums import OnRowSelect, ResponseView
from api.common.formatters import id2title
from api.models import ExperimentalDesign, BiosampleCharacteristics, Provenance
from api.models.base_models import GenericDataModel
from api.models.base_response_models import PagedResponseModel
from api.models.track import ExtendedGenericTrack, GenericTrack

# note this is a generic data model so that we can add summary fields (e.g., counts) as needed
class FILERTrackBrief(SQLModel, GenericTrack):
    assay: Optional[str]
    

class FILERTrack(SQLModel, ExtendedGenericTrack):  
    assay: Optional[str]
    
    # FILER properties
    file_name: Optional[str]
    index_url: Optional[str]
    md5sum: Optional[str]
    raw_file_url: Optional[str]
    raw_file_md5sum: Optional[str]
    bp_covered: Optional[int] 
    number_of_intervals: Optional[int] 
    file_size: Optional[int]
    file_format: Optional[str]
    file_schema: Optional[str]
    
    def get_field_names(self):
        fields = list(self.model_fields.keys())
        if len(self.model_extra) > 0:
            fields += list(self.model_extra.keys())
        return fields
    

    def get_view_config(self, view: ResponseView, **kwargs):
        return super().get_view_config(view, **kwargs)
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.serialize(promoteObjs=True, exclude=['replicates'])
    
    def _build_table_config(self):
        config = super()._build_table_config()
        columns = [ c for c in config['columns'] if c['id'] not in ['biosample_characteristics', 
            'replicates', 'provenance', 'data_source'] ] # data source will be promoted from provenance 
        columns += [ {'id': f, 'header': id2title(f)} for f in BiosampleCharacteristics.model_fields]
        columns += [ {'id': f, 'header': id2title(f)} for f in Provenance.model_fields]
        config.update({'columns': columns })
        return config

class FILERTrackBriefResponse(PagedResponseModel):
    response: List[FILERTrackBrief]
    
    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)

    
class FILERTrackResponse(PagedResponseModel):
    response: List[FILERTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = self.response[0].get_field_names()
        return super().to_text(format, fields=fields)


