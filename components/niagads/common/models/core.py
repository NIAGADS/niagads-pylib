from typing import TypeVar
from niagads.utils.dict import prune
from pydantic import (
    BaseModel,
    ConfigDict,
    model_serializer,
)
from abc import ABC, abstractmethod


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    # note: this ignores the model_config b/c it doesn't run model_dump()

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class CustomBaseModel(BaseModel, ABC):
    model_config = ConfigDict(serialize_by_alias=True, use_enum_values=True)

    @abstractmethod
    def as_info_string(self):
        """serializes model as field=value;... info string"""
        raise NotImplementedError(
            "This is an abstract method; must be implemented for each child model."
        )

    @abstractmethod
    def serialize_as_table(self):
        """returns a {columns: , data: } object for a view table"""
        raise NotImplementedError(
            "This is an abstract method; must be implemented for each child model."
        )

    def as_null_free_json(self):
        return prune(self.model_dump(), removeNulls=True)


T_CustomBaseModel = TypeVar("T_RowModel", bound=CustomBaseModel)
