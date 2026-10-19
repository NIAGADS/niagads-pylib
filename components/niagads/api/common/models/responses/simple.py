from typing import Any, List, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.responses.base import BaseResponseModel

from niagads.utils.string import xstr


class ListResponse(BaseResponseModel):
    """for lists of ids or urls, etc"""

    data: List[Union[str, int, float]]

    def to_delimited_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        if self.is_empty():
            return ""

        return "\n".join([xstr(v) for v in self.data if v is not None])
