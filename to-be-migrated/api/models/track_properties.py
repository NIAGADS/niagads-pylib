
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class ExperimentalDesign(BaseModel):
    antibody_target: Optional[str] = None
    assay: Optional[str] = None
    analysis: Optional[str] = None
    classification: Optional[str] = None
    data_category: Optional[str] = None
    output_type: Optional[str] = None
    is_lifted: Optional[bool] = False
    

class BiosampleCharacteristics(BaseModel):
    system_category: Optional[str] = None
    tissue_category: Optional[str] = None
    # biosample_display: Optional[str] = None
    # biosample_summary: Optional[str] = None
    biosample_term: Optional[str] = Field(default=None, description='mapped ontology term')
    # biosample_term_id: Optional[str] = Field(default=None, description='mapped ontology term identifier')
    life_stage: Optional[str] = Field(default=None, description='donor/sample life stage: adult, fetal, embryo')


class Provenance(BaseModel):
    data_source: Optional[str] = None
    download_url: Optional[str] = None
    release_date: Optional[date] = None
    

class DSSAccession(Provenance):
    data_source: str = "NIAGADS DSS"
    accession: str
    pubmed_id: Optional[str] = None
    attribution: Optional[str] = None
    consortia: Optional[str] = None
    # TODO: collections?
    
    
    