
from datetime import datetime
from typing import Optional

from .base_models import SerializableModel


class Provenance(SerializableModel):
    data_source: Optional[str]
    data_source_version: Optional[str]
    download_url: Optional[str]
    download_date: Optional[datetime] 
    release_date: Optional[datetime] 
    experiment_id: Optional[str]
    project: Optional[str]
    