from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.domain.base import DynamicRecordModel
from niagads.api.common.models.service.request import RequestDataModel
from niagads.common.models.base import CustomBaseModel
from niagads.utils.string import xstr
from pydantic import BaseModel, Field, model_validator


class PaginationDataModel(BaseModel):
    """Captures pagination status."""

    page: int = Field(
        default=1,
        description="if result is paged, indicates the current page of the result; defaults to 1",
    )
    total_num_pages: int = Field(
        default=1,
        description="if the result is paged, reports total number of pages in the full result set (response); defaults to 1",
    )
    paged_num_records: Optional[int] = Field(
        default=None,
        description="number of records in the current paged result set (response)",
    )
    total_num_records: Optional[int] = Field(
        default=None,
        description="total number of records in the full result set (response)",
    )


class BaseResponseModel(BaseModel):
    request: RequestDataModel = Field(
        description="details about the originating request"
    )
    pagination: Optional[PaginationDataModel] = Field(
        default=None, description="pagination status, if the result is paged"
    )
    message: Optional[list[Union[str, dict]]] = Field(
        default=None, description="warning or info message(s) qualifying the response"
    )

    @property
    def is_empty(self):
        return len(self.data) == 0

    @property
    def is_paged(self):
        return self.pagination is not None

    def update_message(self, msg: Union[str, dict]):
        if self.message is None:
            self.message = [msg]
        else:
            self.message.append(msg)


class StandardDataSerializationResponse(BaseResponseModel):
    data: List[CustomBaseModel] = Field(description="a list of one or more records")

    @model_validator(mode="before")
    @classmethod
    def preempt_union_validation(cls, candidate_obj: Any):
        """Guard to preempt FastAPI union validation errors by normalizing ambiguous input types."""
        # wrong serialization
        if isinstance(candidate_obj, (str, int, float, bool)):
            return candidate_obj
        if isinstance(candidate_obj, list):
            # still invalid b/c need a dict w/at least request & data
            return candidate_obj

        if isinstance(candidate_obj, dict):
            if "data" in candidate_obj and "request" in candidate_obj:
                candidate_data = candidate_obj["data"]
                if isinstance(candidate_data, list) and isinstance(
                    candidate_data[0], dict
                ):
                    # convert the data dict to CustomBaseModel child
                    data: list[DynamicRecordModel] = [
                        DynamicRecordModel(**row) for row in candidate_data
                    ]
                    new_obj = {**candidate_obj, "data": data}
                    return cls(**new_obj)

        # otherwise, assume object can be serialized by this response model
        # and or should fail serialization and raise a valid error
        # fall back to normal Pydantic validation

    @property
    def row_data_model(self):
        """get the type of the row model in the response;
        if name is True, return the class name, otherwise
        return the type"""

        data_row_model = self.__class__.model_fields["data"].annotation
        try:  # can't explicity test for List[rowType], so just try
            data_row_model = data_row_model.__args__[
                0
            ]  # rowType = typing.List[RowType]
        except:
            data_row_model = data_row_model

        return data_row_model

    @property
    def row_data_fields(self):
        row_model: CustomBaseModel = self.row_data_model
        return row_model.get_model_fields_from_class(sort=True)

    def to_text(self, incl_header=True, null_str: str = DEFAULT_NULL_STRING):
        if self.is_empty():
            if incl_header:
                return "\t".join(self.row_data_fields)
            else:
                return ""

        else:
            output_buffer: list = []
            for index, row in enumerate(self.data, start=1):
                if incl_header and index == 1:
                    row_str = row.to_delimited_text(
                        incl_header=True, null_str=DEFAULT_NULL_STRING
                    )
                else:
                    row_str = row.to_delimited_text(
                        incl_header=False, null_str=DEFAULT_NULL_STRING
                    )
                output_buffer.append(row_str)

        return "\t".join(output_buffer)


class MessageResponse(BaseResponseModel):
    data: Dict[str, Any]

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        raise NotImplementedError(
            "`to_text` conversion not implemented for MessageResponse"
        )


class ListResponse(BaseResponseModel):
    data: List[Union[str, int, float]]

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        if self.is_empty():
            return ""

        return "\n".join([xstr(v) for v in self.data if v is not None])
