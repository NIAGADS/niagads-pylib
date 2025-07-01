from typing import Any, List, TypeVar
from niagads.common.models.views.table import TableRow
from niagads.utils.dict import prune
from niagads.utils.string import dict_to_info_string
from pydantic import BaseModel, ConfigDict, model_serializer
from abc import ABC, abstractmethod


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    # note: this ignores the model_config b/c it doesn't run model_dump()

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class AbstractTransformableModel(BaseModel, ABC):
    @abstractmethod
    def as_info_string(self) -> str:
        """serializes model as field=value;... info string"""
        pass

    @abstractmethod
    def as_list(self, fields: list = None) -> List[Any]:
        """returns list of model attribute values; if fields is specified returns the selected field values in the listed order"""
        pass

    @abstractmethod
    def as_table_row(self) -> TableRow:
        """returns a {columns: , data: } object for a view table; with custom logic for composite attributes"""
        pass

    @classmethod
    @abstractmethod
    def table_fields(self, asStr: bool = False):
        """get fields for tabular data views"""
        pass


class TransformableModel(AbstractTransformableModel):
    model_config = ConfigDict(serialize_by_alias=True, use_enum_values=True)

    def null_free_dump(self):
        return prune(self.model_dump(), removeNulls=True)

    # abstract method overrides

    def as_info_string(self):
        return dict_to_info_string(self.null_free_dump())

    def as_list(self, fields=None):
        if fields is None:
            return list(self.model_dump().values())
        else:
            return [v for k, v in self.model_dump() if k in fields]

    def as_table_row(self):
        row = {k: getattr(self, k) for k in self.table_fields(asStr=True)}
        return TableRow(**row)

    @classmethod
    def table_fields(self, asStr: bool = False):
        return self.get_fields(asStr)

    @classmethod
    def get_fields(self, asStr: bool = False):
        """get model fields either as name: FieldInfo pairs or as a list of names if asStr is True"""
        return (
            list(self.__class__.model_fields.keys())
            if asStr
            else self.__class__.model_fields
        )

    def __str__(self):
        return self.as_info_string()


T_TransformableModel = TypeVar("T_TransformableModel", bound=TransformableModel)
