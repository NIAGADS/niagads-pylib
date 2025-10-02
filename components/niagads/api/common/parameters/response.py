from enum import auto

from niagads.enums.core import CaseInsensitiveEnum
from niagads.api.common.parameters.enums import EnumParameter


class ResponseContent(EnumParameter):
    """enum for allowable response types"""

    FULL = auto()
    COUNTS = auto()
    IDS = auto()
    BRIEF = auto()
    URLS = auto()
    # SUMMARY = auto()  - for data summaries? or separate endpoints

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Type of information returned by the query."
        return message + f" {super().get_description()}" if inclValues else message

    @classmethod
    def descriptive(cls, inclUrls=False, description=False):
        """return descriptive formats only (usually for metadata)"""
        exclude = (
            [ResponseContent.IDS, ResponseContent.COUNTS]
            if inclUrls
            else [ResponseContent.IDS, ResponseContent.URLS, ResponseContent.COUNTS]
        )
        subset = cls.exclude("descriptive_only_content", exclude)
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def data(cls, description=False):
        """return data formats only"""
        subset = cls.exclude(
            "data_only_content",
            [ResponseContent.IDS, ResponseContent.URLS, ResponseContent.BRIEF],
        )
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def full_data(cls, description=False):
        """return full data formats only"""
        subset = cls.exclude(
            "full_data_only_content",
            [ResponseContent.IDS, ResponseContent.URLS, ResponseContent.BRIEF],
        )
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset


class ResponseFormat(EnumParameter):
    """enum for allowable response / output formats"""

    JSON = auto()
    TEXT = auto()
    VCF = auto()
    BED = auto()

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Response format.  If a non-text `view` is specified, the response format will default to `JSON`"
        return message + f" {super().get_description()}" if inclValues else message

    @classmethod
    def generic(cls, description=False):
        subset = cls.exclude(
            "generic_formats", [ResponseFormat.VCF, ResponseFormat.BED]
        )
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def functional_genomics(cls, description=False):
        subset = cls.exclude("functional_genomics_formats", [ResponseFormat.VCF])
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def variant_score(cls, description=False):
        subset = cls.exclude("variant_score_formats", [ResponseFormat.BED])
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset


class ResponseView(EnumParameter):
    """enum for allowable views"""

    TABLE = auto()
    IGV_BROWSER = auto()
    DEFAULT = auto()

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Visual representation of the data.  Select `DEFAULT` for TEXT or JSON response."
        return message + f" {super().get_description()}" if inclValues else message

    @classmethod
    def table(cls, description=False):
        subset = cls.exclude("table_views", [ResponseView.IGV_BROWSER])
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset
