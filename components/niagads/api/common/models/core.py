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

from typing import Any, Dict, List, Self, TypeVar

from niagads.common.models.core import TransformableModel
from niagads.api_common.views.table import TableCellType, TableColumn, TableRow
from pydantic import ConfigDict, Field


class RowModel(TransformableModel):
    """
    The RowModel base class defines class methods
    expected for these objects to generate standardized API responses
    and adds member functions for generating table responses
    """

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


# FIXME: move this - but where?
class ResultSize(ORMCompatibleDynamicRowModel):
    num_results: int = Field(
        title="Num. Results",
        description="number of search results",
    )

    def __str__(self):
        return self.as_info_string()

    @staticmethod
    def sort(results: List[Self], reverse=True) -> List[Self]:
        """sorts a list of track results"""
        return sorted(results, key=lambda item: item.num_results, reverse=reverse)
