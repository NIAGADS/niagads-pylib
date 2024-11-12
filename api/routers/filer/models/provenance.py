
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from api.response_models.base_models import SerializableModel


class Provenance(SerializableModel, BaseModel):
    data_source: Optional[str]
    data_source_version: Optional[str]
    download_url: Optional[str]
    download_date: Optional[datetime] 
    release_date: Optional[datetime] 
    experiment_id: Optional[str]
    project: Optional[str]
    