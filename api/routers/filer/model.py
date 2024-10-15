from sqlmodel import Field, SQLModel, Column

# typing
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import TEXT, JSONB, TIMESTAMP
from datetime import datetime
from typing import Optional
from pydantic import computed_field

from api.internal.constants import DATASOURCE_URLS
from niagads.filer.parser import split_replicates


class Track(SQLModel, table=True):
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
    filer_release_date: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
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

    searchable_text: Optional[str] = Field(sa_column=Column(TEXT))
    
    @computed_field
    @property
    def genome_browser_track_schema(self) -> str:    
        if self.file_schema is None:
            return None
        schema = self.file_schema.split('|')
        return schema[0]
    
    @computed_field
    @property 
    def genome_browser_track_type(self) -> str:
        # TODO: interactions
        if 'QTL' in self.feature_type:
            return 'qtl'
        else:
            return 'annotation'
    
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
    
    # FIXME: this does not work b/c it does not include the computed fields
    def clean(self):
        internalFields = ['biological_replicates', 'technical_replicates', 
            'searchable_text',
            'genome_browser_track_schema', 'genome_browser_track_type',
            '_sa_instance_state']
        x = vars(self).items()
        for k,v in vars(self).items():
            print(k, v)
        return { k: v for k, v in vars(self).items() if k not in internalFields}
