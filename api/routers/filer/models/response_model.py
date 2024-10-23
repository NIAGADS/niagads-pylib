import json
from sqlmodel import SQLModel
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Optional, List

from niagads.utils.list import find

from api.response_models import BiosampleCharacteristics, id2title, PagedResponseModel, BaseResponseModel, SerializableModel

class TrackPublicBase(SQLModel):
    track_id: str
    name: str
    description: Optional[str] 
    genome_build: Optional[str]
    feature_type: Optional[str]
    data_category: Optional[str]
    antibody_target: Optional[str]
    assay: Optional[str]
    is_lifted: Optional[bool]
    data_source: Optional[str]

    @classmethod
    def table_columns(cls):
        """ Return a column object for niagads-viz-js/Table """
        fields = list(cls.__fields__.keys()) + list(BiosampleCharacteristics.__annotations__.keys())
        fields.remove('biosample_characteristics')
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields if f != 'data_source_url'] 
        
        # some additional formatting
        index: int = find(columns, 'is_lifted', 'id', returnValues=False)
        columns[index[0]].update({'type': 'boolean', 'description': 'data have been lifted over from an earlier genome build'})
        
        return columns

class TrackPublic(SerializableModel, TrackPublicBase):    
    # experimental design
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

        
class TrackResponse(BaseResponseModel):
    response: List[TrackPublic]

class InformativeTrackSummary(SerializableModel, TrackPublicBase):
    hit_count: int
    life_stage: Optional[str] = None
    biosample_term: Optional[str] = None
    system_category: Optional[str] = None
    tissue_category: Optional[str] = None
    biosample_display: Optional[str] = None
    biosample_summary: Optional[str] = None
    biosample_term_id: Optional[str] = None
    
class InformativeTrackSummaryResponse(PagedResponseModel):
    response: List[InformativeTrackSummary]