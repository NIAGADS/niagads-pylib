"""
Base Pydantic model classes for NIAGADS data models.
"""

from datetime import date, datetime
from enum import Enum, auto

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import prune
from niagads.utils.string import dict_to_info_string, xstr
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FieldSerializationInfo,
    SerializerFunctionWrapHandler,
    field_serializer,
    model_serializer,
)


class SerializationOptions(CaseInsensitiveEnum):
    ENUMS_AS_NAME = auto()  # return enums as names instead of default value
    ENUMS_AS_VALUE = auto()
    EXCLUDE_EMPTY_OBJECTS = auto()  # exclude empty dicts and lists
    EMBEDDED_TEXT = auto()  # return only fields relevant for generating embeddings


class CustomBaseModel(BaseModel):
    """
    custom base model for all model types
    """

    model_config = ConfigDict(serialize_by_alias=True, populate_by_name=True)

    @field_serializer("*")
    def serialize_types(self, v, _info: FieldSerializationInfo):
        """custom field handlers
        - dates to iso-format strings
        - return enum names instead of values, if requested
        """
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        if (
            _info.context is not None
            and _info.context.get(SerializationOptions.ENUMS_AS_NAME) is True
        ):
            if isinstance(v, (Enum, CaseInsensitiveEnum)):
                return v.name

        if (
            _info.context is not None
            and _info.context.get(SerializationOptions.ENUMS_AS_VALUE) is True
        ):
            if isinstance(v, (Enum, CaseInsensitiveEnum)):
                return v.value

        return v

    @model_serializer(mode="wrap", when_used="always")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, _info: FieldSerializationInfo
    ):
        """custom serializer to handle context, while respecting serialization options"""
        data = handler(self)

        # exclude byte data
        data = {
            k: v
            for k, v in data.items()
            if not isinstance(v, (bytes, bytearray, memoryview))
        }

        # Check if we should exclude empty objects (empty lists and dicts)
        if (
            _info.context is not None
            and _info.context.get(SerializationOptions.EXCLUDE_EMPTY_OBJECTS) is True
        ):
            data = {
                k: v
                for k, v in data.items()
                if not (isinstance(v, (list, dict)) and len(v) == 0)
            }

        # : Exclude fields marked for embedding exclusion
        if (
            _info.context is not None
            and _info.context.get(SerializationOptions.EMBEDDED_TEXT) is True
        ):
            # Get field metadata
            excluded_fields = {
                field_name
                for field_name, field_info in self.__class__.model_fields.items()
                if field_info.json_schema_extra
                and field_info.json_schema_extra.get("exclude_from_embeddings") is True
            }
            data = {k: v for k, v in data.items() if k not in excluded_fields}

        return data

    @staticmethod
    def boolean_null_check(v):
        if v is None:
            return False
        else:
            return v

    def clean_model_dump(self, exclude_none: bool = True):
        return self.model_dump(
            exclude=True, exclude_none=exclude_none, exclude_unset=exclude_none
        )

    def to_info_string(self):
        """Return a compact info string representation of the model.

        Uses model_dump to serialize the model, excluding unset and None fields, and
        formats as a single-line string.

        Returns:
            str: Info string summarizing model fields and values.
        """
        data = self.clean_model_dump()
        return dict_to_info_string(data)

    def to_value_list(self, fields: list[str] = None):
        """Return model values as a list, ordered by fields.

        Args:
            fields (list[str], optional): List of field names to include and order.
                If None, uses all model fields sorted by 'order' metadata.

        Returns:
            list: List of field values in the specified order.
        """
        sorted_fields = self.get_model_fields(sort=True) if fields is None else fields
        data = self.clean_model_dump(exclude_none=False)
        return [data.get(f) for f in sorted_fields]

    def to_delimited_text(
        self, fields=None, incl_header: bool = True, null_str="NA", delimiter="\t"
    ):
        """Return model as a delimited text row (e.g., tab-delimited).

        Args:
            fields (list[str], optional): Field names to include and order. If None, uses all model fields sorted by 'order' metadata.
            incl_header (bool): If True, include a header row with field names. Defaults to True.
            null_str (str): String to use for null/missing values. Defaults to "NA".
            delimiter (str): Delimiter to use between values. Defaults to tab ("\t").

        Returns:
            str: Delimited string of field values (with optional header).
        """

        values = self.to_value_list(fields=fields)
        delimited_text = delimiter.join([xstr(v, null_str=null_str) for v in values])

        if incl_header:
            header = delimiter.join(fields)
            delimited_text = "\n".join([header, delimited_text])

        return delimited_text

    def has_extras(self):
        """test if extra model fields are present"""
        if isinstance(self.model_extra, dict):
            return len(self.model_extra) > 0

        return False

    @classmethod
    def get_model_fields_from_class(cls, sort: bool = False):
        """Classmethod for getting model field names

        Sorting uses the 'order' key in json_schema_extra if available.

        Args:
            sort (bool): If True, fields are sorted by 'order' metadata; otherwise,
            original order is used.

        Returns:
            list[str]: List of model field names
        """
        # get fields, ignore those set to exclude=True
        fields: dict = [
            (k, v)
            for k, v in cls.model_fields.items()
            if not getattr(v, "exclude", False)
        ]
        if sort:
            fields = sorted(
                fields,
                key=lambda item: (item[1].json_schema_extra or {}).get(
                    "order", float("inf")
                ),
            )

        return list(fields.keys())

    def get_model_fields(self, sort: bool = False):
        """Return model field names for an instantiated class

        Includes extra fields if present. Sorting uses the 'order' key in
        json_schema_extra if available.

        Args:
            sort (bool): If True, fields are sorted by 'order' metadata; otherwise,
            original order is used.

        Returns:
            list[str]: List of model field names, including extras if present.
        """

        # get fields, ignore those set to exclude=True
        fields: list = [
            (k, v)
            for k, v in self.__class__.model_fields.items()
            if not getattr(v, "exclude", False)
        ]
        if sort:
            fields = sorted(
                fields,
                key=lambda item: (item[1].json_schema_extra or {}).get(
                    "order", float("inf")
                ),
            )

        # _ hear means ignore and discard the other part of the tuple
        field_names = [k for k, _ in fields]

        if self.has_extras():
            field_names.extend(self.model_extra.keys())

        return field_names

    def __str__(self):
        return self.to_delimited_text()

    def __repr__(self):
        return self.to_info_string()
