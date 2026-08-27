from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.common.models.base import CustomBaseModel
from niagads.utils.string import xstr


class VCFSerializationMixin:
    def to_vcf(self):
        pass


class BEDSerializationMixin:
    def to_bed(self):
        # get valid model fields, make sure they include genomic region or chrm, start, end etc
        # print header
        # for each row in data, print row w/bed fields
        pass
