from abc import ABC, abstractmethod
from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.common.models.base import CustomBaseModel


class TextSerializationMixin:
    def to_delimited_text(
        self: CustomBaseModel,
        incl_header: bool = True,
        null_str: str = DEFAULT_NULL_STRING,
        delimiter="\t",
    ):
        if self.is_empty():
            return ""

        fields = self.get_model_fields(sort=True)

        values = self.model_dump()
        delimited_text = delimiter.join(
            [null_str if values[f] is None else xstr(values[f]) for f in fields]
        )

        if incl_header:
            header = delimiter.join(fields)
            delimited_text = delimiter.join([header, delimited_text])

        return delimited_text


class VCFSerializationMixin:
    def to_vcf(self):
        pass


class BEDSerializationMixin:
    def to_bed(self):
        # get valid model fields, make sure they include genomic region or chrm, start, end etc
        # print header
        # for each row in data, print row w/bed fields
        pass


class AbstractViewMixin(ABC):
    @abstractmethod
    def to_table(self, id: str = None, title: str = None):
        """return a table view response"""
        pass
