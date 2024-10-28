from fastapi.encoders import jsonable_encoder
from sqlmodel import SQLModel
from typing import Optional, Dict, List, Union
from typing_extensions import Self

from api.common.formatters import id2title

from .base_models import BaseResponseModel

class GenomeBrowserConfig(SQLModel):
    track_id: str
    name: str
    browser_track_format: Optional[str]
    url: str
    index_url: Optional[str]
    
    @classmethod
    def view_table_columns(cls: Self):
        """ Return a column object for niagads-viz-js/Table """
        fields = list(cls.model_fields.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields] 

        return columns    
    
class GenomeBrowserExtendedConfig(GenomeBrowserConfig):
    description: Optional[str]
    feature_type: str
    data_source: str
    browser_track_category: Optional[str]
    biosample_characteristics: Optional[Dict[str, str]]
    experimental_design: Optional[Dict[str, str]]
    
"""
NOTE: design decision - why two response models instead of:
class GenomeBrowserConfigResponse(BaseModel):
    response: Union[List[GenomeBrowserConfig] | List[GenomeBrowserExtendedConfig]]
    
b/c in this case, I need to serialize manually: Track (from DB model) -> dict -> Config model
for each Track

in the case below, FAST-API & Pydantic do the work
"""    
class GenomeBrowserConfigResponse(BaseResponseModel):
    response: List[GenomeBrowserConfig]
    
class GenomeBrowserExtendedConfigResponse(BaseResponseModel):
    response: List[GenomeBrowserExtendedConfig]

