from sqlmodel import Field, SQLModel, Column

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import TEXT, JSONB, TIMESTAMP
from datetime import date
from typing import Optional
from pydantic import computed_field

from niagads.filer.parser import split_replicates

from api.config.urls import DATASOURCE_URLS
from api.models.base_models import SerializableModel
from api.models.track_properties import ExperimentalDesign, Provenance

# Developer Note: not setting a default for all optionals b/c coming from
# the SQLModel, which will have nulls if no value

class FILERAccession(Provenance):
    data_source_version: Optional[str] = None
    download_date: Optional[date] = None
    project: Optional[str] = None # FIXME: make this == collections: List[str]?

class Collection(SQLModel, table=True):
    __tablename__ = "filercollection"
    __bind_key__ = 'filer'
    __table_args__ = {'schema': 'serverapplication'}
    
    collection_id: int = Field(default=None, primary_key=True)
    name: str
    description: str = Field(sa_column=Column(TEXT))
    tracks_are_sharded: bool
    

class TrackCollection(SQLModel, table=True):
    __tablename__ = "filercollectiontracklink"
    __bind_key__ = 'filer'
    __table_args__ = {'schema': 'serverapplication'}
    
    collection_track_link_id: str = Field(default=None, primary_key=True)
    track_id: str = Field(foreign_key="track.track_id")
    collection_id: int = Field(foreign_key="collection.collection_id")
    

class Track(SQLModel, SerializableModel, table=True):
    __tablename__ = "filertrack"
    __bind_key__ = 'filer'
    __table_args__ = {'schema': 'serverapplication'}
    
    track_id: str = Field(default=None, primary_key=True)
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
    download_date: Optional[date] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
    release_date: Optional[date] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
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
    filer_release_date: Optional[date] = Field(sa_column=Column(TIMESTAMP(timezone=False)))

    searchable_text: Optional[str] = Field(sa_column=Column(TEXT))
    is_shard: Optional[bool]
    shard_parent_track_id: Optional[str]
    
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
    def provenance(self) -> FILERAccession:
        props = { field: getattr(self, field) for field in FILERAccession.model_fields }
        return FILERAccession(**props)

        
    @computed_field 
    @property
    def experimental_design(self) -> ExperimentalDesign: # required for browser config
        props = { field : getattr(self, field) for field in ExperimentalDesign.model_fields }
        return ExperimentalDesign(**props)
    
    # =================================
    # GENOME BROWSER FIELDS
    # =================================
    @computed_field
    @property
    def browser_track_name(self) -> str:
        return self.track_id + ': ' + self.name.replace(f'{self.feature_type} {self.feature_type}', self.feature_type)
    
    @computed_field
    @property
    def browser_track_category(self) -> str: # TODO: be more specific? e.g., data category?
        return 'Functional Genomics'
    

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
    
