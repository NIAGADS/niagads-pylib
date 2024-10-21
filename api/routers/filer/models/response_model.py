from sqlmodel import SQLModel
# typing
from datetime import datetime
from typing import Optional

class TrackPublic(SQLModel):    
    track_id: str
    name: str
    description: Optional[str] 
    genome_build: Optional[str]
    feature_type: Optional[str]
    
    # biosample
    biosample_characteristics: Optional[dict]
        
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

