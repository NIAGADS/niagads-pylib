from enum import auto
from typing import Type

from fastapi.exceptions import RequestValidationError
from niagads.enums.core import CaseInsensitiveEnum
from niagads.open_access_api_base_models.responses.core import ResponseModel
from niagads.open_access_api_parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from pydantic import BaseModel, field_validator, model_validator


# FIXME: is this really necessary? onRowSelect can be driven by the target view
class OnRowSelect(CaseInsensitiveEnum):
    """enum for allowable NIAGADS-viz-js/Table onRowSelect actions"""

    ACCESS_ROW_DATA = auto()
    UPDATE_GENOME_BROWSER = auto()
    UPDATE_LOCUSZOOM = auto()




