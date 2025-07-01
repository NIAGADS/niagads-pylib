"""core defines a generic row model
Most API responses are tables represented as lists of objects,
wherein each item in the list is a row in the table.

A Row Model is the data hash (key-value pairs) defining the table row.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar

from niagads.common.models.core import CustomBaseModel
from niagads.common.models.views.table import TableCellType, TableColumn
from niagads.open_access_api_common.config.constants import DEFAULT_NULL_STRING
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.utils.string import xstr
from pydantic import ConfigDict, Field


class AbstractRowModel(ABC):
    @classmethod
    @abstractmethod
    def table_columns(self, **kwargs):
        """table columns"""
        raise NotImplementedError(
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )

    @abstractmethod
    def to_view_data(self, view: ResponseView, **kwargs):
        # transform data into format needed for a view
        raise NotImplementedError(
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )

    @abstractmethod
    def to_text(self, format: ResponseFormat, **kwargs):
        # transform data into text response
        raise NotImplementedError(
            f"This is an abstract method; must be implemented for the child model: {self.__class__.__name__}."
        )


class RowModel(CustomBaseModel, AbstractRowModel):
    """
    The RowModel base class defines class methods
    expected for these objects to generate standardized API responses
    """

    # START abstract methods from CustomBaseModel
    def as_info_string(self):
        return super().as_info_string()

    def as_table_row(self):
        return self.model_dump()

    def as_list(self, fields=None):
        if fields is None:
            return [str(v) for v in self.model_dump().values()]
        else:
            return [str(v) for k, v in self.model_dump() if k in fields]

    @classmethod
    def table_fields(cls, asStr: bool = False):
        return list(cls.model_fields.keys()) if asStr else cls.model_fields

    # END abstract methods from CustomBaseModel

    # START Abstract methods from AbstractRowModel
    @classmethod
    def table_columns(self, **kwargs):
        fields = self.table_fields()
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

    def to_view_data(self, view: ResponseView, **kwargs):
        match view:
            case ResponseView.TABLE:
                return self.as_table_row()

            case _:
                return self.model_dump()

    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get("nullStr", DEFAULT_NULL_STRING)
        match format:
            case ResponseFormat.TEXT:
                fields = self.table_fields(asStr="true")
                values = self.as_list(fields=fields)
                return "\t".join(
                    [xstr(v, nullStr=nullStr, dictsAsJson=False) for v in values]
                )
            case _:
                raise NotImplementedError(
                    f"Text transformation `{format.value}` not supported for a generic data response"
                )


# allows you to set a type hint to a class and all its subclasses
# as long as type is specified as Type[T_RowModel]
# Type: from typing import Type
T_RowModel = TypeVar("T_RowModel", bound=RowModel)


class DynamicRowModel(RowModel):
    """A row model that allows for extra, unknown fields."""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")

    def has_extras(self):
        """test if extra model fields are present"""
        if isinstance(self.model_extra, dict):
            return len(self.model_extra) > 0

        return False

    def table_fields(self, asStr: bool = False):
        fields = super().table_fields()
        if self.has_extras():
            extras = {k: Field() for k in self.model_extra.keys()}
            fields += extras

        return list(fields.keys()) if asStr else fields

    def to_text(self, format, **kwargs):
        return super().to_text(format, **kwargs)

    def to_view_data(self, view, **kwargs):
        return super().to_view_data(view, **kwargs)
