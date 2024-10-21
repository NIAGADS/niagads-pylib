from fastapi.encoders import jsonable_encoder
from sqlmodel import SQLModel
from typing import Optional, Dict

class BrowserTrack(SQLModel):
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
    
    def serialize(self, **kwargs):
        """Return a dict which contains only serializable fields."""
        return jsonable_encoder(self.model_dump())



