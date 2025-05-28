from enum import auto
from typing import Any, Dict, List, Optional, Union

from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel

T_JSON = Union[Dict[str, Any], List[Any], int, float, str, bool, None]


class OpenAPIxGroupTag(BaseModel):
    name: str
    tags: List[str]


class OpenAPITag(BaseModel):
    name: str
    description: Optional[str] = None
    summary: Optional[str] = None
    externalDocs: Optional[dict[str, str]] = None


class OpenAPISpec(BaseModel):
    title: str
    description: str
    summary: str
    version: str
    admin_email: str
    service_url: str
    openapi_tags: List[OpenAPITag]


class RecordType(CaseInsensitiveEnum):
    GENE = auto()
    VARIANT = auto()
    # STRUCTURAL_VARIANT = auto()
    SPAN = auto()
    TRACK = auto()

    def __str__(self):
        return self.name.lower()
