from sqlmodel import SQLModel
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Any, Dict, Optional, List, Union
from typing_extensions import Self
from pydantic import model_validator

from niagads.utils.list import find

from api.common.constants import JSON_TYPE
from api.common.enums import ResponseFormat
from api.common.formatters import id2title
from api.response_models import PagedResponseModel, GenericDataModel
from api.response_models.base_models import RowModel
from .biosample_characteristics import BiosampleCharacteristics

# note this is a generic data model so that we can add summary fields (e.g., counts) as needed
class FILERTrackBrief(SQLModel, RowModel, GenericDataModel):
    track_id: str
    name: str
    genome_build: Optional[str]
    feature_type: Optional[str]
    is_lifted: Optional[bool]
    data_source: Optional[str]
    data_category: Optional[str]
    assay: Optional[str]
    
    @model_validator(mode='before')
    @classmethod
    def allowable_extras(cls: Self, data: Union[Dict[str, Any]]):
        """ for now, allowable extras are just counts, prefixed with `num_` """
        if type(data).__base__ == SQLModel: # then there are no extra fields
            return data
        modelFields = cls.model_fields.keys()
        return {k:v for k, v in data.items() if k in modelFields or k.startswith('num_')}

    def get_view_config(self, view: ResponseFormat) -> JSON_TYPE:
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self._build_table_config()
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
        
    
    def to_view_data(self, view: ResponseFormat) -> JSON_TYPE:
        """ covert row data to view formatted data """
        return self.serialize()

    def _build_table_config(self):
        """ Return a column object for niagads-viz-js/Table """
        fields = list(self.model_fields.keys())
        if len(self.model_extra) > 0:
            fields += list(self.model_extra.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields]
            
        # update type of is_lifted to boolean
        index: int = find(columns, 'is_lifted', 'id', returnValues=False)
        columns[index[0]].update({'type': 'boolean', 'description': 'data have been lifted over from an earlier genome build'})
        options: dict = {
            'disableColumnFilters': True, # FIXME: Remove when column filters are implemented
        }
        if 'num_overlaps' in fields:
            options.update({'rowSelect': {
                    'header': 'Select',
                    'enableRowMultiSelect': True,
                    'rowId': 'track_id'
                }})
        return {'columns': columns, 'options': options}
    

class FILERTrack(FILERTrackBrief):  
    description: Optional[str]   
    
    # experimental design
    antibody_target: Optional[str]
    replicates: Optional[dict]
    analysis: Optional[str]
    classification: Optional[str]
    output_type: Optional[str]
    experiment_info: Optional[str]
    # biosample
    biosample_characteristics: Optional[BiosampleCharacteristics]
    # provenance
    data_source_version: Optional[str]
    data_source_url: Optional[str]
    download_url: Optional[str]
    download_date: Optional[datetime]
    release_date: Optional[datetime] 
    filer_release_date: Optional[datetime] 
    experiment_id: Optional[str]
    project: Optional[str]
    
    # FILER properties
    file_name: Optional[str]
    url: Optional[str]
    index_url: Optional[str]
    md5sum: Optional[str]
    raw_file_url: Optional[str]
    raw_file_md5sum: Optional[str]
    bp_covered: Optional[int] 
    number_of_intervals: Optional[int] 
    file_size: Optional[int]
    file_format: Optional[str]
    file_schema: Optional[str]

    def get_view_config(self, view):
        return super().get_view_config(view)
    
    def to_view_data(self, view):
        return self.serialize(promoteObjs=True, exclude=['replicates'])
    
    def _build_table_config(self):
        config = super()._build_table_config()
        columns = [ c for c in config['columns'] if c['id'] not in ['biosample_characteristics', 'replicates'] ] 
        columns += [ {'id': f, 'header': id2title(f)} for f in BiosampleCharacteristics.model_fields]
        config.update({'columns': columns })
        return config

class FILERTrackBriefResponse(PagedResponseModel):
    response: List[FILERTrackBrief]
    
class FILERTrackResponse(PagedResponseModel):
    response: List[FILERTrack]



