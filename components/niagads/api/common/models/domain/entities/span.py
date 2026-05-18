from typing import Optional
from niagads.api.common.models.domain.base import ORMCompatibleRecord
from niagads.common.genomic.regions.models import GenomicRegion
from niagads.genome_reference.human import HumanGenome
from niagads.genome_reference.types import Strand
from pydantic import Field


class SpanDescriptor(ORMCompatibleRecord, GenomicRegion):

    inclusive_end: Optional[bool] = Field(exclude=True)

    @classmethod
    def get_model_fields_from_class(cls, sort: bool = False):
        return ["chromosome", "start", "end", "strand", "length"]

    def get_model_fields(self, sort=False):
        return self.__class__.get_model_fields_from_class()
