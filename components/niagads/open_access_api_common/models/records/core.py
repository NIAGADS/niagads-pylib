"""core defines a generic row model
Most API responses are tables represented as lists of objects,
wherein each item in the list is a row in the table.

A Row Model is the data hash (key-value pairs) defining the table row.
"""

from typing import Any, Dict, List, TypeVar

from niagads.common.models.core import CompositeAttributeModel
from niagads.open_access_api_common.config.constants import DEFAULT_NULL_STRING
from niagads.open_access_api_common.models.views.table.cells import TableCellType
from niagads.open_access_api_common.models.views.table.core import TableColumn
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.utils.string import xstr
from pydantic import BaseModel, ConfigDict


class RowModel(CompositeAttributeModel):
    """
    The RowModel base class defines class methods
    expected for these objects to generate standardized API responses
    """

    @classmethod
    def get_model_fields(cls):
        return list(cls.model_fields.keys())

    def has_extras(self):
        """test if extra model fields are present"""
        return len(self.model_extra) > 0

    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()

    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get("nullStr", DEFAULT_NULL_STRING)
        match format:
            case ResponseFormat.TEXT:
                values = list(self.model_dump().values())
                return "\t".join(
                    [xstr(v, nullStr=nullStr, dictsAsJson=False) for v in values]
                )
            case _:
                raise NotImplementedError(
                    f"Text transformation `{format.value}` not supported for a generic data response"
                )

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        match view:
            case ResponseView.TABLE:
                return self._get_table_view_config(**kwargs)
            case ResponseView.IGV_BROWSER:
                raise NotImplementedError("IGVBrowser view coming soon")
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def _assign_table_cell_type(self, fieldId: str, fieldInfo) -> TableCellType:
        if fieldId == "p_value":
            return TableCellType.PVALUE

        if "url" in fieldId:
            return TableCellType.LINK

        match str(fieldInfo.annotation):
            case s if "str" in s:
                return TableCellType.TEXT
            case s if "bool" in s:
                return TableCellType.BOOLEAN
            case s if "int" in s:
                return TableCellType.FLOAT
            case s if "float" in s:
                return TableCellType.FLOAT
            case _:
                return TableCellType.ABSTRACT

    def _generate_table_columns(self, model: BaseModel, **kwargs):
        fields = model.model_fields
        columns: List[TableColumn] = [
            TableColumn(
                id=k,
                header=info.title if info.title is not None else k,
                description=info.description,
                type=self._assign_table_cell_type(k, info),
            )
            for k, info in fields.items()
        ]

        return columns

    def _get_table_view_config(self, **kwargs):
        # NOTE: options are handled in front-end applications
        return {"columns": self._generate_table_columns(self)}


# allows you to set a type hint to a class and all its subclasses
# as long as type is specified as Type[T_RowModel]
# Type: from typing import Type
T_RowModel = TypeVar("T_RowModel", bound=RowModel)


class DynamicRowModel(RowModel):
    """A row model that allows for extra, unknown fields."""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")

    @classmethod
    def get_model_fields(cls):
        return list(cls.model_fields.keys())

    def get_instantiated_fields(self):
        fields = self.__class__.get_model_fields()
        if isinstance(self.model_extra, dict):
            if len(self.model_extra) > 0:
                fields += list(self.model_extra.keys())
        return fields
