"""Common Pydantic `Models` for the Open Access API services

includes the following:

* core: foundational models for most data
* responses: response models and models defining response model properities or configuration
* record: core representation of API entity records
* query: sql query objects

"""

""" `RowModel`
Most API responses are tables represented as lists of objects,
wherein each item in the list is a row in the table.

A Row Model is the data hash (key-value pairs) defining the table row.
"""

from typing import Any, Dict, List, TypeVar

from niagads.common.models.core import TransformableModel
from niagads.common.models.views.table import TableCellType, TableColumn, TableRow
from niagads.open_access_api_common.config.constants import DEFAULT_NULL_STRING
from pydantic import ConfigDict, Field


class RowModel(TransformableModel):
    """
    The RowModel base class defines class methods
    expected for these objects to generate standardized API responses
    and adds member functions for generating table responses
    """

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
        return self._sort_fields(self.get_model_fields(), asStr=asStr)

    # END abstract methods from TransformableModel

    def table_columns(self, **kwargs):
        fields = self.table_fields(**kwargs)
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

    def as_text(self, fields=None, nullStr=DEFAULT_NULL_STRING, **kwargs):
        """return row as tab-delimited plain text"""
        if fields is None:
            fields = self.table_fields(asStr="true")
        values = self.as_list(fields=fields)
        return "\t".join([nullStr if v is None else str(v) for v in values])


# allows you to set a type hint to a class and all its subclasses
# as long as type is specified as Type[T_RowModel]
# Type: from typing import Type
T_RowModel = TypeVar("T_RowModel", bound=RowModel)


class ORMCompatibleRowModel(RowModel):
    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)


class DynamicRowModel(RowModel):
    """A row model that allows for extra, unknown fields."""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")

    def has_extras(self):
        """test if extra model fields are present"""
        if isinstance(self.model_extra, dict):
            return len(self.model_extra) > 0

        return False

    def table_fields(self, asStr: bool = False, **kwargs):
        fields = super().table_fields(asStr, **kwargs)

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
