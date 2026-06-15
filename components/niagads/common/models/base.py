"""
Base Pydantic model classes for NIAGADS data models.
"""

from datetime import date, datetime
from enum import Enum, auto
from typing import TypeVar

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import prune
from pydantic import (
    BaseModel,
    ConfigDict,
    FieldSerializationInfo,
    SerializerFunctionWrapHandler,
    field_serializer,
    model_serializer,
)


class SerializationOptions(CaseInsensitiveEnum):
    ENUMS_AS_NAME = auto()  # return enums as names instead of default value
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


T_BaseModel = TypeVar("T_BaseModel", bound=CustomBaseModel)
