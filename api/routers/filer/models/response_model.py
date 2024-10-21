import json
from sqlmodel import SQLModel
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Optional, List

from niagads.utils.list import find

from api.response_models import BiosampleCharacteristics, id2title, VizTable, VizTableOptions

class TrackPublic(SQLModel):    
    track_id: str
    name: str
    description: Optional[str] 
    genome_build: Optional[str]
    feature_type: Optional[str]
    
    # biosample
    biosample_characteristics: Optional[BiosampleCharacteristics]
        
    # experimental design
    replicates: Optional[dict]
    antibody_target: Optional[str]
    assay: Optional[str]
    analysis: Optional[str]
    classification: Optional[str]
    data_category: Optional[str]
    output_type: Optional[str]
    is_lifted: Optional[bool]
    experiment_info: Optional[str]
        
    # provenance
    data_source: Optional[str]
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


    def serialize(self, expandObjects=False):
        """Return a dict which contains only serializable fields."""
        data:dict = jsonable_encoder(self.model_dump())
        
        if expandObjects:
            data.update(data.pop('biosample_characteristics', None))
            data.update({'replicates': json.dumps(data['replicates'])})

        return data
    
    @classmethod
    def table_columns(cls):
        """ Return a column object for niagads-viz-js/Table """
        
        fields = list(cls.__annotations__.keys()) + list(BiosampleCharacteristics.__annotations__.keys())
        fields.remove('biosample_characteristics')
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields if f != 'data_source_url'] 
        
        # some additional formatting
        index: int = find(columns, 'is_lifted', 'id', returnValues=False)
        columns[index[0]].update({'type': 'boolean', 'description': 'data have been lifted over from an earlier genome build'})
        
        return columns


