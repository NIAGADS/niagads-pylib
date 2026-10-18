from typing import Any, Dict, List, Optional, Self, Union

from niagads.api.common.models.records.types import ORMCompatibleRecord

from niagads.common.gene.models.record import GeneIdentifier, GeneRecord
from niagads.common.genomic.regions.models import GenomicRegion
from pydantic import ConfigDict, Field, ModelWrapValidatorHandler, model_validator


class GeneDescriptor(GeneIdentifier, ORMCompatibleRecord):
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
    )
    location: Optional[str] = Field(
        default=None,
        title="Location",
        description="genomic location delimiting the footprint (span) of the gene",
    )

    def __str__(self):
        return self.id

    @model_validator(mode="before")
    @classmethod
    def extract_nested_fields(cls, data: Union[dict, Any]):
        """
        Extract nested fields from ORM object and assign to top-level fields.

        Handles both ORM objects and dictionaries, extracting gene descriptor
        fields from the document's nomenclature and gene structure objects.
        """

        updated_data = data if isinstance(data, dict) else data.model_dump()

        # FIXME: developer's note -> figure out why IdMixin is not working
        updated_data["id"] = updated_data.get("source_id")

        nomenclature = updated_data.get("nomenclature")
        if nomenclature:
            updated_data["gene_symbol"] = nomenclature.get("gene_symbol")

        gene_structure = updated_data.get("gene_structure")
        if gene_structure:
            updated_data["location"] = gene_structure.get("location")

        return updated_data


class GeneBrief(GeneDescriptor, ORMCompatibleRecord):
    model_config = ConfigDict(is_summary=True)

    gene_type: Optional[str] = Field(
        default=None,
        title="Gene Type",
        description="biological type or classification of the gene",
    )
    gene_name: Optional[str] = Field(
        default=None,
        title="Gene Name",
        description="official gene name",
    )
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
    def extract_nested_fields(cls, data: Union[dict, Any]):
        """
        Extract nested fields from ORM object and assign to top-level fields.

        Handles both ORM objects and dictionaries, extracting gene descriptor
        fields from the document's nomenclature and gene structure objects.
        """
        updated_data = GeneDescriptor.extract_nested_fields(data)

        nomenclature = updated_data.get("nomenclature")
        updated_data["gene_name"] = nomenclature.get("gene_name")
        updated_data["synonyms"] = nomenclature.get("synonyms")

        gene_structure = updated_data.get("gene_structure")
        updated_data["cytogenic_location"] = gene_structure.get("cytogenic_location")

        return updated_data


class Gene(GeneBrief, GeneRecord, ORMCompatibleRecord):
    nomenclature: Optional[Dict[str, Any]] = Field(exclude=True)
    synonyms: Optional[List[str]] = Field(
        default=None, title="Aliases", description="gene symbol synonyms or aliases"
    )

    @model_validator(mode="before")
    def extract_nested_fields(cls, data: Union[dict, Any]):
        """
        Extract nested fields from ORM object and assign to top-level fields.

        Handles both ORM objects and dictionaries, extracting gene descriptor
        fields from the document's nomenclature and gene structure objects.
        """
        updated_data = GeneBrief.extract_nested_fields(data)
        gene_structure = updated_data.get("gene_structure")
        gene_structure.pop("location", None)
        gene_structure.pop("cytogenic_location", None)

        return updated_data
