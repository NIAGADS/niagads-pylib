from typing import List, Optional
from fastapi.exceptions import RequestValidationError

from pydantic import BaseModel, computed_field

from api.common.enums import CacheKeyQualifier, ResponseContent, CacheNamespace
from api.common.helpers import Parameters, ResponseConfiguration, RouteHelper, PaginationCursor
from api.common.types import Range
from api.models.base_models import CacheKeyDataModel

from .constants import CACHEDB_PARALLEL_TIMEOUT
from ..dependencies.parameters import InternalRequestParameters

class GenomicsRouteHelper(RouteHelper):  
    
    def __init__(self, managers: InternalRequestParameters, responseConfig: ResponseConfiguration, params: Parameters):
        super().__init__(managers, responseConfig, params)
        self._managers: InternalRequestParameters = managers