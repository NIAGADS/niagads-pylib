from sqlmodel import SQLModel
from typing import Any, Dict, Optional, List, Union
from typing_extensions import Self
from pydantic import BaseModel, model_validator

from niagads.utils.list import find

from api.common.constants import JSON_TYPE
from api.common.enums import OnRowSelect, ResponseFormat, ResponseView
from api.common.formatters import id2title
from api.models import ExperimentalDesign, BiosampleCharacteristics, Provenance
from api.models.base_models import GenericDataModel
from api.models.base_response_models import PagedResponseModel

# note this is a generic data model so that we can add summary fields (e.g., counts) as needed
class FILERTrackBrief(SQLModel, GenericDataModel):
    track_id: str
    name: str
    genome_build: Optional[str]
    feature_type: Optional[str]
    is_lifted: Optional[bool]
    data_source: Optional[str]
    data_category: Optional[str]
    assay: Optional[str]
    url: Optional[str]
    
    @model_validator(mode='before')
    @classmethod
    def allowable_extras(cls: Self, data: Union[Dict[str, Any]]):
        """ for now, allowable extras are just counts, prefixed with `num_` """
        if type(data).__base__ == SQLModel or isinstance(data, str) or not isinstance(data, dict): 
            # then there are no extra fields or FASTAPI is attempting to serialize
            # unnecessarily when returning a Union[ResponseType Listing]
            return data
        modelFields = cls.model_fields.keys()
        return {k:v for k, v in data.items() if k in modelFields or k.startswith('num_')}

    def get_view_config(self, view: ResponseView, **kwargs) -> JSON_TYPE:
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self._build_table_config()
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
    
    def to_view_data(self, view: ResponseView, **kwargs) -> JSON_TYPE:
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
        options = {}
        if 'num_overlaps' in fields:
            options.update({'rowSelect': {
                    'header': 'Select',
                    'enableMultiRowSelect': True,
                    'rowId': 'track_id',
                    'onRowSelectAction': OnRowSelect.ACCESS_ROW_DATA
                }})
            fields.remove('num_overlaps')
            fields.insert(0, 'num_overlaps') # so that it is in the first 8 and displayed by default
        if len(fields) > 8:
            options.update({'defaultColumns': fields[:8]})
        return {'columns': columns, 'options': options}
    

class FILERTrack(FILERTrackBrief):  
    experimental_design: Optional[ExperimentalDesign]
    
    # biosample
    biosample_characteristics: Optional[BiosampleCharacteristics]
    
    # provenance
    provenance: Optional[Provenance]
    
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

    def to_view(self, view: ResponseView, **kwargs):
        return super().to_view(view, **kwargs)
    
class FILERTrackResponse(PagedResponseModel):
    response: List[FILERTrack]

    def to_view(self, view: ResponseView, **kwargs):
        return super().to_view(view, **kwargs)


