from typing import Any, Dict, List, Optional, Union

from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel, Field, model_validator

T_JSON = Union[Dict[str, Any], List[Any], int, float, str, bool, None]


class BaseTag(BaseModel):
    name: str
    xSortOrder: int = Field(serialization_alias="x-sortOrder")

    def model_dump(self, **kwargs) -> dict[str, Any]:
        return super().model_dump(by_alias=True, **kwargs)


class OpenAPITag(BaseTag):
    description: Optional[str] = None
    summary: Optional[str] = None
    externalDocs: Optional[dict[str, str]] = None
    xTraitTag: Optional[bool] = Field(default=False, serialization_alias="x-traitTag")
    xDisplayName: Optional[str] = Field(
        default=None, serialization_alias="x-displayName"
    )

    @model_validator(mode="after")
    def set_display_name(self):
        if self.xDisplayName is None:
            self.xDisplayName = self.name
        return self


class OpenAPIxTagGroup(BaseTag):
    tags: List[OpenAPITag]

    def model_dump(self, **kwargs) -> dict[str, Any]:
        obj = super().model_dump()
        # just return the "name" for the tags, but sort by sort order
        tags = obj["tags"]
        obj["tags"] = [t["name"] for t in sorted(tags, key=lambda d: d["x-sortOrder"])]

        return obj


class OpenAPISpec(BaseModel):
    title: str
    description: str
    summary: str
    version: str
    admin_email: str
    service_url: str
    openapi_tags: List[OpenAPITag]
    xtag_groups: Optional[List[OpenAPIxTagGroup]] = None
