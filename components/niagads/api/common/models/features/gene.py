from typing import Dict, List, Optional, Union

from niagads.database.schemas.gene.composite_attributes import (
    GOAnnotation,
    PathwayAnnotation,
)
from niagads.api.common.models.core import RowModel
from niagads.api.common.models.response.core import RecordResponse
from pydantic import Field
from niagads.api.common.models.features.genomic import GenomicRegion


class GeneFeature(RowModel):
    id: str = Field(title="Ensembl ID", description="Ensembl gene identifier")
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
        serialization_alias="symbol",
    )

    def __str__(self):
        return self.id

    # should allow to fill from SQLAlchemy ORM model
    # model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class Gene(GeneFeature):
    gene_type: Optional[str] = Field(default=None, serialization_alias="type")
    gene_name: Optional[str] = Field(default=None, serialization_alias="name")
    synonyms: Optional[List[str]] = Field(
        default=None, title="Aliases", descriptions="gene symbol synonyms or aliases"
    )
    location: GenomicRegion = Field(
        title="Location",
        description="genomic location delimiting the footprint (span) of the gene",
    )
    cytogenic_location: Optional[str] = Field(
        default=None,
        title="Cytogenic Location",
        description="mapping the gene to a band of the chromosome",
    )

    def __str__(self):
        return self.as_info_string()

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)
        if self.synonyms is not None:
            obj["synonyms"] = self._list_to_string(self.synonyms, delimiter=delimiter)

        # promote the location fields
        del obj["location"]
        obj.update(self.location._flat_dump())
        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()
        del fields["location"]
        fields.update(GenomicRegion.get_model_fields())

        return list(fields.keys()) if as_str else fields


class AnnotatedGene(Gene):
    nomenclature: Optional[Dict[str, Union[str, int]]] = None
    go_annotation: Optional[List[GOAnnotation]] = None
    pathway_membership: Optional[List[PathwayAnnotation]] = None

    def as_info_string(self):
        raise NotImplementedError("Not implemented for Annotated Genes")

    def as_list(self, fields=None):
        raise NotImplementedError("Not implemented for Annotated Genes")

    def as_table_row(self, **kwargs):
        raise NotImplementedError("Not implemented for Annotated Genes")


class GeneFunction(GOAnnotation, RowModel):
    def __str__(self):
        return self.as_info_string()

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)
        if self.evidence is not None:
            obj["evidence"] = self._list_to_string(self.evidence, delimiter=delimiter)
        return obj


class GenePathwayMembership(PathwayAnnotation, RowModel):
    def __str__(self):
        return self.as_info_string()


class GeneAnnotationResponse(RecordResponse):
    data: Union[
        List[GenePathwayMembership],
        List[GeneFunction],
        List[RowModel],
    ]


class AbridgedGeneResponse(RecordResponse):
    data: List[Gene]


class GeneResponse(RecordResponse):
    data: List[AnnotatedGene]

    def to_table(self, id=None, title=None):
        raise NotImplementedError("Table views not avaialble for `FULL` gene records.")

    def to_text(self, incl_header=False, null_str=None):
        raise NotImplementedError(
            "Plain text responses not available for `FULL` gene records."
        )


class RegionGene(RowModel):
    gene: GeneFeature = Field(title="Gene")
    gene_type: str = Field(title="Gene Type")
    location: GenomicRegion
    range_relation: str = Field(
        title="Range Relation",
        description="indicates location of gene relative to the queries region",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["location"]
        obj.update(self.location._flat_dump())

        del obj["gene"]
        obj.update(self.gene._flat_dump())

        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()
        del fields["location"]
        fields.update(GenomicRegion.get_model_fields())
        del fields["gene"]
        fields.update(GeneFeature.get_model_fields())

        return list(fields.keys()) if as_str else fields
