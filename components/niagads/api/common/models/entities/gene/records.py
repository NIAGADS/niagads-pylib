from typing import Dict, List, Optional, Union

from niagads.api.common.models.records.base import ORMCompatibleRecord
from niagads.api.common.models.records.mixins import DynamicMixin
from niagads.common.gene.models.annotation import (
    GOAssociation,
    PathwayMembership,
)
from niagads.common.gene.models.record import GeneRecord
from niagads.common.genomic.regions.models import GenomicRegion
from pydantic import ConfigDict, Field, model_validator


class GeneDescriptor(GeneRecord):
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
        serialization_alias="symbol",
    )
    location: Optional[GenomicRegion] = Field(
        default=None,
        title="Location",
        description="genomic location delimiting the footprint (span) of the gene",
    )

    def __str__(self):
        return self.id


class GeneBrief(GeneDescriptor, ORMCompatibleRecord):
    model_config = ConfigDict(is_summary=True)

    gene_type: Optional[str] = Field(default=None, serialization_alias="type")
    gene_name: Optional[str] = Field(default=None, serialization_alias="name")
    synonyms: Optional[List[str]] = Field(
        default=None, title="Aliases", description="gene symbol synonyms or aliases"
    )
    cytogenic_location: Optional[str] = Field(
        default=None,
        title="Cytogenic Location",
        description="mapping the gene to a band of the chromosome",
    )

    def __str__(self):
        return self.to_info_string()

    @model_validator(mode="before")
    def extract_nested_fields(cls, values: Union[dict, any]):
        """
        Extract nested fields from ORM object and assign to top-level fields.

        Handles both ORM objects and dictionaries, extracting gene descriptor
        fields from the document's nomenclature and gene structure objects.
        """
        if not isinstance(values, dict):
            values = values.model_dump()

        nomenclature = values.get("nomenclature")
        if isinstance(nomenclature, dict):
            values.setdefault("gene_symbol", nomenclature.get("gene_symbol"))
            values.setdefault("gene_name", nomenclature.get("gene_name"))
            values.setdefault("synonyms", nomenclature.get("synonyms"))

        gene_structure = values.get("gene_structure")
        if isinstance(gene_structure, dict):
            values.setdefault("location", gene_structure.get("location"))
            values.setdefault(
                "cytogenic_location", gene_structure.get("cytogenic_location")
            )

        return values


class Gene(GeneRecord, ORMCompatibleRecord):
    @model_validator(mode="before")
    def extract_nested_fields(cls, values: Union[dict, any]):
        """Extract public gene fields from the document's nested fields."""
        if not isinstance(values, dict):
            values = values.model_dump()

        nomenclature = values.get("nomenclature")
        if isinstance(nomenclature, dict):
            values.setdefault("gene_symbol", nomenclature.get("gene_symbol"))

        gene_structure = values.get("gene_structure")
        if isinstance(gene_structure, dict):
            values.setdefault("location", gene_structure.get("location"))

        return values
