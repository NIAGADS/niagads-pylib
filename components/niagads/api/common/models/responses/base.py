from collections.abc import Mapping, Sequence
from typing import Any, Dict, Optional, Union

from lxml import etree
from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.context.request import RequestDetails
from niagads.api.common.models.responses.pagination import PaginationState
from niagads.common.models.base import CustomBaseModel
from pydantic import Field


class BaseResponseModel(CustomBaseModel):
    _xml_root: str = "response"
    request: RequestDetails = Field(description="details about the originating request")
    pagination: Optional[PaginationState] = Field(
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

    def to_xml(self):
        """Build an XML response element from model or mapping data."""
        root = etree.Element(self._xml_root)
        self.__append_xml(root, self.model_dump(exclude_none=True))
        return etree.tostring(root, encoding="unicode")

    def __append_xml(self, parent, value, name=None):
        """Append a mapping, sequence, or scalar value to an XML element.

        Args:
            parent: XML element receiving the serialized value.
            value: Value to append to the XML tree.
            name: Element name for scalar or sequence values.
        """

        if isinstance(value, Mapping):
            for key, child_value in value.items():
                self.__append_xml(parent, child_value, key)
            return

        if isinstance(value, Sequence) and not isinstance(value, str):
            for item in value:
                self.__append_xml(parent, item, name)
            return

        element = etree.SubElement(parent, name)
        element.text = str(value)


class MessageResponse(BaseResponseModel):
    data: Dict[str, Any]

    def to_delimited_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        raise NotImplementedError(
            "`to_delimited_text` conversion not implemented for MessageResponse"
        )
