from niagads.utils.dict import prune
from pydantic import BaseModel, model_serializer


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)
