from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Dict, List, TypeVar

from niagads.common.models.views.table import TableRow
from niagads.utils.dict import prune
from niagads.utils.string import dict_to_info_string
from pydantic import BaseModel, ConfigDict, model_serializer


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
    def as_table_row(self, **kwargs) -> TableRow:
        """returns a {columns: , data: } object for a view table; with custom logic for composite attributes"""
        pass

    @classmethod
    @abstractmethod
    def table_fields(self, asStr: bool = False, **kwargs):
        """get fields for tabular data views"""
        pass


class TransformableModel(AbstractTransformableModel):
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
            return [v for k, v in self._flat_dump().items() if k in fields]

    def as_table_row(self, **kwargs):
        obj = self._flat_dump(delimiter=" // ")
        row = {k: obj.get(k, "NA") for k in self.table_fields(asStr=True)}
        return TableRow(**row)

    def _sort_fields(self, fields: Dict[str, Any], asStr: bool = False):
        sortedFields = dict(
            sorted(
                fields.items(),
                key=lambda item: (
                    item[1].json_schema_extra.get("order")
                    if item[1].json_schema_extra
                    and "order" in item[1].json_schema_extra
                    else float("inf")
                ),
            )
        )
        return [k for k in sortedFields.keys()] if asStr else sortedFields

    def table_fields(self, asStr: bool = False, **kwargs):
        return self._sort_fields(self.get_fields(), asStr=asStr)

    # note: not a classmethod b/c will need to be overridden to add model_extras
    # when relevant
    def get_fields(self, asStr: bool = False):
        """get model fields either as name: FieldInfo pairs or as a list of names if asStr is True"""
        return self.get_model_fields(asStr)

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
