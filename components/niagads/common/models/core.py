from typing import TypeVar

from niagads.utils.dict import prune
from niagads.utils.string import dict_to_info_string
from pydantic import BaseModel, ConfigDict, model_serializer


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    # note: this ignores the model_config b/c it doesn't run model_dump()

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class TransformableModel(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True, use_enum_values=True)

    def null_free_dump(self):
        return prune(self.model_dump(), removeNulls=True)

    @staticmethod
    def _list_to_string(arr: list, delimiter="|"):
        uniqueValues = set([str(a) for a in arr])
        return delimiter.join(uniqueValues) if arr is not None else None

    def _flat_dump(self, nullFree: bool = False, delimiter="|"):
        """function for creating a flat dump; i.e., remove nesting"""
        return self.null_free_dump() if nullFree else self.model_dump()

    # abstract method overrides

    def as_info_string(self):
        return dict_to_info_string(self._flat_dump(nullFree=True))

    def as_list(self, fields=None):
        if fields is None:
            return list(self._flat_dump().values())
        else:
            obj = self._flat_dump()
            return [obj.get(k) for k in fields]

    @classmethod
    def get_model_fields(cls, asStr: bool = False):
        """classmethod for getting model fields either as name: FieldInfo pairs or as a list of names if asStr is True"""
        return (
            [
                (v.serialization_alias if v.serialization_alias is not None else k)
                for k, v in cls.model_fields.items()
                if not v.exclude
            ]
            if asStr
            else {
                v.serialization_alias if v.serialization_alias is not None else k: v
                for k, v in cls.model_fields.items()
                if not v.exclude
            }
        )

    def __str__(self):
        return self.as_info_string()


T_TransformableModel = TypeVar("T_TransformableModel", bound=TransformableModel)
