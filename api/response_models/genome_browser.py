from fastapi.encoders import jsonable_encoder
from sqlmodel import SQLModel
from typing import Optional, Dict, List
from typing_extensions import Self

from api.response_models.formatters import id2title

from .base_models import BaseResponseModel

class GenomeBrowserConfig(SQLModel):
    track_id: str
    name: str
    description: Optional[str]
    feature_type: str
    data_source: str
    biosample_characteristics: Optional[Dict[str, str]]
    experimental_design: Optional[Dict[str, str]]
    browser_track_category: Optional[str]
    browser_track_format: Optional[str]
    url: str
    index_url: Optional[str]
    
    @classmethod
    def view_table_columns(cls: Self):
        """ Return a column object for niagads-viz-js/Table """
        fields = list(cls.model_fields.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields] 

        return columns
    
class GenomeBrowserConfigResponse(BaseResponseModel):
    response: List[GenomeBrowserConfig]

