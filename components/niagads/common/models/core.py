from typing import List, TypeVar
from niagads.utils.dict import prune
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )

    @abstractmethod
    def as_list(self, fields: list = None):
        """returns list of model attribute values; if fields is specified returns the selected field values in the listed order"""
        raise NotImplementedError(
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )

    @abstractmethod
    def as_table_row(self):
        """returns a {columns: , data: } object for a view table; with custom logic for composite attributes"""
        raise NotImplementedError(
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )

    @classmethod
    @abstractmethod
    def table_fields(self, asStr: bool = False):
        """get fields for tabular data views"""
        raise NotImplementedError(
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )

    def null_free_dump(self):
        return prune(self.model_dump(), removeNulls=True)


T_CustomBaseModel = TypeVar("T_RowModel", bound=CustomBaseModel)
