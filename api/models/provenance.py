from datetime import date
from typing import Optional

from .base_models import SerializableModel

class Provenance(SerializableModel):
    data_source: Optional[str]
    download_url: Optional[str]
    release_date: Optional[date] 

class FILERAccession(Provenance):
    data_source_version: Optional[str]
    download_date: Optional[date] 
    project: Optional[str] # FIXME: make this == collections: List[str]?
    
class DSSAccession(Provenance):
    data_source: str = "NIAGADS DSS"
    accession: str
    pubemd_id: str
    attribution: str
    # TODO: collections?
    