from datetime import date
from typing import Optional

from .base_models import SerializableModel

class Provenance(SerializableModel):
    data_source: Optional[str]
    data_source_version: Optional[str]
    download_url: Optional[str]
    download_date: Optional[date] 
    release_date: Optional[date] 
    experiment_id: Optional[str]
    project: Optional[str]
    