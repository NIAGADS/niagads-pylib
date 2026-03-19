"""
Base Pydantic model classes for NIAGADS data models.
"""

from datetime import date, datetime
from enum import Enum
from typing import TypeVar

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import prune
from pydantic import BaseModel, ConfigDict, field_serializer, model_serializer


class CustomBaseModel(BaseModel):
    """
    custom base model for all model types
    """

    model_config = ConfigDict(serialize_by_alias=True, populate_by_name=True)

    @field_serializer("*")
    def serialize_types(self, v, _info):
        if _info.context is not None and _info.context.get("enums_as_name") == True:
            if isinstance(v, Enum):
                return v.name
            if isinstance(v, CaseInsensitiveEnum):
                return v.name
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    @staticmethod
    def boolean_null_check(v):
        if v is None:
            return False
        else:
            return v


T_BaseModel = TypeVar("T_BaseModel", bound=CustomBaseModel)
