from typing import Generic, get_args

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.records.types import RecordT
from niagads.api.common.models.responses.base import BaseResponseModel


class RecordResponse(BaseResponseModel, Generic[RecordT]):
    data: list[RecordT]

    @property
    def row_data_model(self):
        """the `type` of the generic RecordT"""

        return get_args(type(self).model_fields["data"].annotation)[0]

    @property
    def row_data_fields(self):
        row_model: RecordT = self.row_data_model
        return row_model.get_model_fields_from_class(sort=True)

    def to_delimited_text(
        self, *, incl_header: bool = False, null_str: str = DEFAULT_NULL_STRING
    ):
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


class RecordMappingResponse(BaseResponseModel, Generic[RecordT]):
    data: dict[str, list[RecordT]]
