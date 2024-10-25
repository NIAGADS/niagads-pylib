from sqlmodel import SQLModel
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Optional, List
from typing_extensions import Self

from niagads.utils.list import find

from api.common.formatters import id2title
from api.response_models import PagedResponseModel, BaseResponseModel, SerializableModel
from .biosample_characteristics import BiosampleCharacteristics

class FILERTrackBrief(SQLModel, SerializableModel):
    track_id: str
    name: str
    genome_build: Optional[str]
    feature_type: Optional[str]
    is_lifted: Optional[bool]
    data_source: Optional[str]
    data_category: Optional[str]
    assay: Optional[str]

    @classmethod
    def view_table_columns(cls: Self):
        """ Return a column object for niagads-viz-js/Table """
        fields = list(cls.model_fields.keys())
        if 'biosample_characteristics' in fields:
            fields += list(BiosampleCharacteristics.model_fields.keys())
            fields.remove('biosample_characteristics')
        
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields if f != 'data_souce_url']
            
        # update type of is_lifted to boolean
        index: int = find(columns, 'is_lifted', 'id', returnValues=False)
        columns[index[0]].update({'type': 'boolean', 'description': 'data have been lifted over from an earlier genome build'})
        
        return columns

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


class FILERTrackOverlapSummary(FILERTrackBrief):
    hit_count: int
    """
    life_stage: Optional[str] = None
    system_category: Optional[str] = None
    tissue_category: Optional[str] = None
    biosample_term: Optional[str] = None
    biosample_term_id: Optional[str] = None
    """
    
class FILERTrackBriefResponse(BaseResponseModel):
    response: List[FILERTrackBrief]

class FILERTrackBriefPagedResponse(PagedResponseModel):
    response: List[FILERTrackBrief]
    
class FILERTrackResponse(BaseResponseModel):
    response: List[FILERTrack]

class FILERTrackPagedResponse(PagedResponseModel):
    response: List[FILERTrack]

class FILERTrackOverlapPagedResponse(PagedResponseModel):
    response: List[FILERTrackOverlapSummary]