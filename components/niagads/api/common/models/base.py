"""`RowModel`
Most API responses are tables represented as lists of objects,
wherein each item in the list is a row in the table.

A Row Model is the data hash (key-value pairs) defining the table row.
ORM compatible Row Models can be insantiated from SQLAlchemy results
"""

from typing import Any, Dict, List, TypeVar

from niagads.api.common.views.table import TableCellType, TableColumn, TableRow
from niagads.utils.list import list_to_string
from niagads.utils.string import dict_to_info_string
from pydantic import BaseModel, ConfigDict, Field


class RowModel(BaseModel):
    """
    The RowModel base class defines class methods
    expected for these objects to generate standardized API responses
    and adds member functions for generating table responses
    """

    model_config = ConfigDict(serialize_by_alias=True)

    @staticmethod
    def boolean_null_check(v):
        # FIXME: is this really needed?
        if v is None:
            return False
        else:
            return v

    def flat_dump(self, null_free: bool = False, delimiter="|"):
        """function for creating a flat dump; i.e., flattens nested models, lists to strings
        for table views, etc"""
        for k, v in self.__dict__.items():
            if isinstance(v, (dict, BaseModel)):
                raise NotImplementedError(
                    f"Field '{k}' in '{self.__class__.__name__}' is complex (type: {type(v).__name__}). "
                    "Please override the _flat_dump method in your subclass "
                    "to flatten nested structures."
                )
        return (
            self.model_dump(exclude_none=True, exclude_unset=True)
            if null_free
            else self.model_dump()
        )

    @staticmethod
    def _flatten_list_to_string(arr: list, delimiter="|"):
        """flat dump helper; flattens a list to a string"""
        return (
            list_to_string(arr, delim=delimiter, as_set=True)
            if arr is not None
            else None
        )

    def as_info_string(self):
        return dict_to_info_string(self.flat_dump(null_free=True))

    def as_list(self, fields=None):
        if fields is None:
            return list(self.flat_dump().values())
        else:
            obj = self.flat_dump()
            return [obj.get(k) for k in fields]

    @classmethod
    def list_model_fields(cls, as_str: bool = False):
        """classmethod for getting model fields either as name: FieldInfo pairs or as a list of names if as_str is True
        again for views"""
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

    def as_text(self, fields=None, null_str="NA", **kwargs):
        """return row as tab-delimited plain text"""
        if fields is None:
            fields = self.get_table_fields(as_str="true")
        values = self.as_list(fields=fields)
        return "\t".join([null_str if v is None else str(v) for v in values])

    def as_table_row(self, **kwargs):
        obj = self._flat_dump(delimiter=" // ")
        row = {k: obj.get(k, "NA") for k in self.get_table_fields(as_str=True)}
        return TableRow(**row)

    def get_table_fields(self, as_str: bool = False, **kwargs):
        return self._sort_fields(self.get_model_fields(), as_str=as_str)

    def generate_table_columns(self, **kwargs):
        fields = self.get_table_fields(**kwargs)
        columns: List[TableColumn] = [
            TableColumn(
                id=k,
                header=info.title if info.title is not None else k,
                description=info.description,
                type=TableCellType.from_field(info),
            )
            for k, info in fields.items()
        ]

        return columns

    def _sort_fields(self, fields: Dict[str, Any], as_str: bool = False):
        sorted_fields = dict(
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
        return [k for k in sorted_fields.keys()] if as_str else sorted_fields


# allows you to set a type hint to a class and all its subclasses
# as long as type is specified as Type[T_RowModel]
# Type: from typing import Type
T_RowModel = TypeVar("T_RowModel", bound=RowModel)


class ORMCompatibleRowModel(RowModel):
    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DynamicRowModel(RowModel):
    """A row model that allows for extra, unknown fields."""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")

    def has_extras(self):
        """test if extra model fields are present"""
        if isinstance(self.model_extra, dict):
            return len(self.model_extra) > 0

        return False

    def get_table_fields(self, as_str: bool = False, **kwargs):
        fields = super().get_table_fields(as_str, **kwargs)

        if self.has_extras():
            extras = {k: Field() for k in self.model_extra.keys()}
            if isinstance(fields, list):
                fields.extend(list(extras.keys()))
            else:
                fields.update(extras)

        return fields


class ORMCompatibleDynamicRowModel(DynamicRowModel):
    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)
