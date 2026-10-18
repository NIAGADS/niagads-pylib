from typing import Generic

from niagads.api.common.models.records.types import RecordT
from niagads.api.common.models.responses.base import BaseResponseModel


class RecordResponse(BaseResponseModel, Generic[RecordT]):
    data: list[RecordT]


class RecordMappingResponse(BaseResponseModel, Generic[RecordT]):
    data: dict[str, RecordT]
