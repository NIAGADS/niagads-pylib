"""
Base Pydantic model classes for NIAGADS data models.
"""

from datetime import date, datetime
from enum import Enum
from typing import TypeVar

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import prune
from niagads.utils.string import dict_to_info_string
from pydantic import BaseModel, ConfigDict, field_serializer, model_serializer


class null_freeModel(BaseModel):
    """a pydantic base model where attributes with NULL values
    (e.g., None, 'NULL') are removed during serialization
    """

    # note: this ignores the model_config b/c it doesn't run model_dump()

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class TransformableModel(BaseModel):
    """
    Pydantic base model with utility methods for data transformation and null handling.
    """

    model_config = ConfigDict(serialize_by_alias=True)

    @field_serializer("*")
    def serialize_types(self, v, _info):
        if _info.context.get("enums_as_name") == True:
            if isinstance(v, Enum):
                return v.name
            if isinstance(v, CaseInsensitiveEnum):
                return v.name
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    def null_free_dump(self):
        # FIXME: why not just self.model_dump(exclude_unset=True, exclude_none=True)
        return prune(self.model_dump(), removeNulls=True)

    @staticmethod
    def boolean_null_check(v):
        if v is None:
            return False
        else:
            return v

    @staticmethod
    def _list_to_string(arr: list, delimiter="|"):
        uniqueValues = set([str(a) for a in arr])
        return delimiter.join(uniqueValues) if arr is not None else None

    def _flat_dump(self, null_free: bool = False, delimiter="|"):
        """function for creating a flat dump; i.e., remove nesting"""
        for k, v in self.__dict__.items():
            if isinstance(v, (dict, BaseModel)):
                raise NotImplementedError(
                    f"Field '{k}' in '{self.__class__.__name__}' is complex (type: {type(v).__name__}). "
                    "Please override the _flat_dump method in your subclass "
                    "to flatten nested structures."
                )
        return self.null_free_dump() if null_free else self.model_dump()

    def as_info_string(self):
        return dict_to_info_string(self._flat_dump(null_free=True))

    def as_list(self, fields=None):
        if fields is None:
            return list(self._flat_dump().values())
        else:
            obj = self._flat_dump()
            return [obj.get(k) for k in fields]

    @classmethod
    def get_model_fields(cls, as_str: bool = False):
        """classmethod for getting model fields either as name: FieldInfo pairs or as a list of names if as_str is True"""
        return (
            [
                (v.serialization_alias if v.serialization_alias is not None else k)
                for k, v in cls.model_fields.items()
                if not v.exclude
            ]
            if as_str
            else {
                v.serialization_alias if v.serialization_alias is not None else k: v
                for k, v in cls.model_fields.items()
                if not v.exclude
            }
        )

    def __str__(self):
        return self.as_info_string()

    def __repr__(self):
        return self.as_info_string()


T_TransformableModel = TypeVar("T_TransformableModel", bound=TransformableModel)
