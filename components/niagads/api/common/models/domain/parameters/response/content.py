from enum import auto
from typing import Self

from niagads.api.common.models.domain.parameters.types import EnumParameter


class ResponseContent(EnumParameter):
    """enum for allowable response types"""

    FULL = auto()
    BRIEF = auto()
    URLS = auto()
    COUNTS = auto()
    IDS = auto()

    @classmethod
    def description(cls, include_values=True):
        message = "Response content (full vs selected subset)"
        return message + f"{super().description()}" if include_values else message

    @classmethod
    def label(cls):
        return "content"

    @classmethod
    def entity_record(cls, has_urls=False) -> Self:
        """return descriptive formats only (usually for metadata)"""
        members = [ResponseContent.FULL, ResponseContent.BRIEF, ResponseContent.IDS]
        if has_urls:
            members.append(ResponseContent.URLS)
        return cls.subset("record_document", members)

    @classmethod
    def feature_record(cls) -> Self:
        """return data formats only"""
        members = [ResponseContent.FULL, ResponseContent.COUNTS]
        return cls.subset("data_only_content", members)


class ResponseFormat(EnumParameter):
    """enum for allowable response / output formats"""

    DEFAULT = auto()
    TEXT = auto()
    TABLE = auto()  # reformat for a NIAGADS UI Table

    @classmethod
    def label(cls):
        return "format"

    @classmethod
    def description(cls, include_values=True):
        message = "Response format."
        return message + f" {super().description()}" if include_values else message
