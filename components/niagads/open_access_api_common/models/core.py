"""Common Pydantic `Models` for the Open Access API services

includes the following:

* core: foundational models for most data and response models
* responses: response models and models defining response model properities or configuration
* data: core representation of API responses as table row of one or more records
* sql:

"""

from typing import List

from fastapi.encoders import jsonable_encoder
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import promote_nested
from pydantic import BaseModel, ConfigDict


class Entity(CaseInsensitiveEnum):
    GENE = "gene"
    VARIANT = "variant"
    SPAN = "span"
    TRACK = "track"

    def __str__(self):
        return self.value.title()
