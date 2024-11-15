from sqlmodel import Field, SQLModel, Column

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import TEXT, JSONB, TIMESTAMP
from datetime import datetime
from typing import Optional
from pydantic import computed_field

from niagads.filer.parser import split_replicates
from niagads.utils.list import qw
from niagads.utils.string import xstr

from api.internal.constants import DATASOURCE_URLS
from api.response_models import SerializableModel, Provenance, ExperimentalDesign

EXPERIMENTAL_DESIGN_FIELDS = qw('project experiment_id antibody_target assay analysis classification data_category output_type is_lifted')

class Track(SQLModel, SerializableModel, table=True):
    __tablename__ = "filertrack"
    __bind_key__ = 'filer'
    __table_args__ = {'schema': 'serverapplication'}
    
    track_id: str = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = Field(sa_column=Column(TEXT))
    genome_build: Optional[str]
    feature_type: Optional[str]
    
    # biosample
    biosample_characteristics: dict | None = Field(sa_column=Column(JSONB))
        
    # experimental design
    biological_replicates: Optional[str]
    technical_replicates: Optional[str]
    antibody_target: Optional[str]
    assay: Optional[str]
    analysis: Optional[str] = Field(sa_column=Column(TEXT))
    classification: Optional[str] = Field(sa_column=Column(TEXT))
    data_category: Optional[str]
    output_type: Optional[str]
    is_lifted: Optional[bool]
    experiment_info: Optional[str] = Field(sa_column=Column(TEXT))
        
    # provenance
    data_source: Optional[str]
    data_source_version: Optional[str]
    download_url: Optional[str]
    download_date: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
    release_date: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
    experiment_id: Optional[str]
    project: Optional[str]
    
    # FILER properties
    file_name: Optional[str]
    url: Optional[str]
    md5sum: Optional[str]
    raw_file_url: Optional[str]
    raw_file_md5sum: Optional[str]
    bp_covered: Optional[int] = Field(sa_column=Column(BigInteger()))
    number_of_intervals: Optional[int] = Field(sa_column=Column(BigInteger()))
    file_size: Optional[int]
    file_format: Optional[str]
    file_schema: Optional[str]
    filer_release_date: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(timezone=False)))

    searchable_text: Optional[str] = Field(sa_column=Column(TEXT))
    
    @computed_field
    @property
    def index_url(self) -> str:
        return self.url + '.tbi'
    
    @computed_field
    @property
    def data_source_url(self) -> str:
        dsKey = self.data_source + '|' + self.data_source_version if self.data_source_version is not None else self.data_source
        try:
            return getattr(DATASOURCE_URLS, dsKey)
        except Exception as e: # TODO: error reporting to admins b/c this is a missing data problem
            return self.data_source
    
    @computed_field
    @property
    def replicates(self) -> dict:
        biological = split_replicates(self.biological_replicates)
        technical = split_replicates(self.technical_replicates)
        
        if biological is None: 
            if technical is None: return None
            return { "technical": technical}
        if technical is None:
            return { "biological": biological}
        
        return { "technical": technical, "biological": biological}
    
    @computed_field
    @property
    def provenance(self) -> Provenance:
        return {
            'data_source' : self.data_source,
            'data_source_version': self.data_source_version,
            'download_url': self.download_url,
            'download_date': self.download_date,
            'release_date': self.release_date,
            'experiment_id': self.experiment_id,
            'project': self.project
        }
    
    # =================================
    # GENOME BROWSER FIELDS
    # =================================
    @computed_field
    @property
    def browser_track_category(self) -> str: # TODO: be more specific? e.g., data category?
        return 'Functional Genomics'
    
    @computed_field 
    @property
    def experimental_design(self) -> ExperimentalDesign: # required for browser config
        return { field : xstr(getattr(self, field), nullStr="NA") for field in EXPERIMENTAL_DESIGN_FIELDS }
            
    @computed_field
    @property
    def browser_track_format(self) -> str:    
        if self.file_schema is None:
            return 'bed'
        schema = self.file_schema.split('|')
        return schema[0]    
    
    @computed_field
    @property 
    def browser_track_type(self) -> str:
        trackType = 'annotation'
        if '|' in self.file_schema:
            schema = self.file_schema.split('|')
            trackType = schema[1]
        return trackType
    
