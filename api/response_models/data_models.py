from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional, Union
from typing_extensions import Self

from ..common.formatters import id2title
from .base_models import GenericDataModel, PagedResponseModel

class BEDFeature(GenericDataModel):
    chrom: str
    chromStart: int
    chromEnd: int
    name: Optional[str] = '.'
    score: Optional[Union[str, int, float]] = '.'
    strand: Optional[str] = '.'
    
    def view_table_columns(self, collapseExtras=True):
        """ Return a column object for niagads-viz-js/Table """
        # NOTE: self.model_fields_set will get both the fields and the extra fields
        fields = list(self.model_fields.keys()) 
        if len(self.model_extra) > 0:
            if collapseExtras: 
                fields = fields + ['additional_fields']
            else:
                fields += list(self.model_extra.keys())
                
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields]
        return columns
    

class BEDResponse(PagedResponseModel):
    response: List[BEDFeature]
    

