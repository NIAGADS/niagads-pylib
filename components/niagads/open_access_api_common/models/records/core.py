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
