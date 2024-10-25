from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any
from typing_extensions import Self

from niagads.filer import BEDFeature as FILERApiBEDFeature, FILERTrackOverlaps

from ..common.formatters import id2title
from .base_models import SerializableModel, PagedResponseModel, BaseResponseModel

# see https://docs.pydantic.dev/latest/concepts/models/#extra-fields 
# for information about extra fields; basically we don't know what information might
# be coming back

# TODO -> export to table; need to serialize the extra as a dict b/c
# it may vary in one response
class BEDFeature(SerializableModel, FILERApiBEDFeature):
    
    @classmethod
    def view_table_columns(cls: Self):
        """ Return a column object for niagads-viz-js/Table """
        raise NotImplementedError('Because a BEDFeature can have extra fields, must generate columns from instantiation')

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
    

    
class BEDResponse(BaseResponseModel):
    response: List[BEDFeature]
    
