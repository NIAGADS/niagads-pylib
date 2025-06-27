from niagads.utils.dict import prune
from pydantic import BaseModel, ConfigDict, model_serializer, model_validator


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class CompositeAttributeModel(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True, use_enum_values=True)
