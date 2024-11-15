from pydantic import Field
from typing import Optional

from api.response_models.base_models import SerializableModel

class ExperimentalDesign(SerializableModel):
    project: Optional[str] = None
    experiment_id: Optional[str] = None
    antibody_target: Optional[str] = None
    assay: Optional[str] = None
    analysis: Optional[str] = None
    classification: Optional[str] = None
    data_category: Optional[str] = None
    output_type: Optional[str] = None
    is_lifted: Optional[bool] = False
    
