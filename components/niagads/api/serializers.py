"""Serialization utilities for API response formats."""

from collections.abc import Mapping, Sequence
from typing import Union

from lxml import etree
from niagads.common.models.base import CustomBaseModel
from pydantic import BaseModel


def xml_resonse_serializer(
    data: Union[type[CustomBaseModel], dict],
    root_name: str = "response",
):
    """Build an XML response element from model or mapping data.

    Args:
        root_name: Name of the root XML element.
        data: Data to serialize into the XML element tree.
    """

    root = etree.Element(root_name)
    __append_xml(root, data)
    return etree.tostring(root, encoding="unicode")


def __append_xml(parent, value, name=None):
    """Append a mapping, sequence, or scalar value to an XML element.

    Args:
        parent: XML element receiving the serialized value.
        value: Value to append to the XML tree.
        name: Element name for scalar or sequence values.
    """

    if isinstance(value, Mapping):
        for key, child_value in value.items():
            __append_xml(parent, child_value, key)
        return

    if isinstance(value, Sequence) and not isinstance(value, str):
        for item in value:
            __append_xml(parent, item, name)
        return

    element = etree.SubElement(parent, name)
    element.text = str(value)
