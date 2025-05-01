from enum import auto
from typing import Annotated, Any, Dict, List, Optional, Union

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import BaseModel, Field, model_validator

T_JSON = Union[Dict[str, Any], List[Any], int, float, str, bool, None]


class RecordType(CaseInsensitiveEnum):
    GENE = auto()
    VARIANT = auto()
    # STRUCTURAL_VARIANT = auto()
    SPAN = auto()
    TRACK = auto()

    def __str__(self):
        return self.name.lower()
