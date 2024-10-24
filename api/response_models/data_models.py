from pydantic import BaseModel, ConfigDict, Field
from typing import List
from typing_extensions import Self

from .formatters import id2title
from .base_models import SerializableModel, PagedResponseModel, BaseResponseModel

# see https://docs.pydantic.dev/latest/concepts/models/#extra-fields 
# for information about extra fields; basically we don't know what information might
# be coming back

# TODO -> export to table; need to serialize the extra as a dict b/c
# it may vary in one response
class BEDFields(SerializableModel, BaseModel):
    chrom: str
    chromStart: int
    chromEnd: int
    name: str
    score: str
    strand: str
    
    __pydantic_extra__: str = Field(init=False)    
    
    model_config = ConfigDict(extra='allow')
    
    @classmethod
    def view_table_columns(cls: Self):
        """ Return a column object for niagads-viz-js/Table """
        fields = list(cls.model_fields.keys()) + list(cls.model_extra.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields if f != 'data_souce_url']
        return columns

    
class BEDResponse(BaseResponseModel):
    response: List[BEDFields]
    
