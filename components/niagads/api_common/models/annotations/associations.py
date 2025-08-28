from enum import auto
from typing import Dict, List, Optional, Union

from niagads.api_common.models.features.variant import AbridgedVariant, Variant
from niagads.common.models.ontology import OntologyTerm
from niagads.common.types import T_PubMedID
from niagads.common.models.composite_attributes.dataset import (
    BiosampleCharacteristics,
    Phenotype,
)
from niagads.api_common.models.core import RowModel
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.parameters.enums import EnumParameter
from pydantic import Field, field_serializer, model_validator


class AssociationTrait(EnumParameter):
    """enum genetic association trait category"""

    AD = auto()
    ADRD = auto()
    BIOMARKER = auto()
    ALL_AD = auto()
    ALL = auto()
    OTHER = auto()

    def __str__(self):
        match self.name:
            case "BIOMARKER":
                return "AD/ADRD Biomarkers"
            case "ALL_ADRD":
                return "All AD/ADRD"
            case "ALL":
                return "All"
            case "OTHER":
                return "Non-AD/ADRD"
            case _:
                return self.name


class AssociationSource(EnumParameter):
    GWAS = auto()
    CURATED = auto()
    ALL = auto()

    def __str__(self):
        return self.value.title()


class VariantAssociation(RowModel):
    variant: AbridgedVariant = Field(title="Variant", order=1)
    test_allele: str = Field(title="Test Allele", order=2)
    p_value: Union[float, str] = Field(title="p-Value", order=3)

    trait: OntologyTerm = Field(title="Trait", description="associated trait", order=4)
    trait_category: str = Field(
        title="Trait Category",
        description="One of AD, ADRD, Biomarker (for AD/ADRD), or Other",
        order=5,
    )
    track_id: Optional[str] = Field(default=None, title="Track ID", order=6)
    track_name: str = Field(
        title="Study",
        serialization_alias="study",
        description="NIAGADS Data Track or published study curated from the literature or a GWAS Catalog",
        order=7,
    )

    pubmed_id: Optional[List[T_PubMedID]] = Field(
        default=None, title="Publication", order=8
    )

    subject_phenotypes: Optional[Phenotype] = Field(default=None, exclude=True)
    biosample_characterisitics: Optional[BiosampleCharacteristics] = Field(
        default=None, exclude=True
    )

    neg_log10_pvalue: float = Field(title="-log10pValue")

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        if self.pubmed_id is not None:
            obj["pubmed_id"] = self._list_to_string(self.pubmed_id, delimiter=delimiter)

        # promote the variant fields
        del obj["variant"]
        obj.update(self.variant._flat_dump())

        del obj["trait"]
        obj.update(self.trait._flat_dump())
        return obj

    @model_validator(mode="before")
    @classmethod
    def process_trait(cls, data: dict):
        """
        promote subject_phenotypes to get trait if trait is
        not already in the response
        """

        # these will happen b/c FastAPI tries all models
        # until it can successfully serialize
        if data is None:
            return data

        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            data = data.model_dump()  # assume data a model

        if data.get("trait") is not None:
            return data

        phenotypes: dict = data.get("subject_phenotypes")
        biosample: dict = data.get("biosample_characteristics")

        if phenotypes is None and biosample is None:
            return data  # again FAST-API attempting to serialize wrong model

        # priority: disease, neuropath, biomarker
        """
        e.g. subject phenotypes
        {
            "disease": [{"term": "Alzheimer's disease", "term_id": "EFO_1001870"}],
            "ethnicity": [{"term": "European", "term_id": "HANCESTRO_0005"}],
            "study_diagnosis": [{"num_cases": 17008, "num_controls": 37154}],
        }
        """
        trait = (
            (phenotypes.get("disease") if phenotypes else None)
            or (phenotypes.get("neuropathology") if phenotypes else None)
            or (biosample.get("biomarker") if biosample else None)
        )

        data["trait"] = OntologyTerm(**trait[0])

        # TODO: study diagnosis?

        return data

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()

        del fields["variant"]
        fields.update(Variant.get_model_fields())

        for k, info in OntologyTerm.get_model_fields().items():
            title = "Trait" if k == "term" else "Mapped Term ID"
            description = (
                "associated phenotype or biomarker"
                if k == "term"
                else "mapped ontologyy term ID for the trait"
            )
            order = (
                fields["trait"].json_schema_extra.get("order") if k == "term" else 1000
            )
            newField = Field(title=title, description=description, order=order)
            fields.update({k: newField})

        del fields["trait"]

        return list(fields.keys()) if as_str else fields

    def get_table_fields(self, as_str=False, **kwargs):
        return super().get_table_fields(as_str, **kwargs)


class GeneVariantAssociation(VariantAssociation):
    relative_position: str = Field(
        title="Relative Position",
        description="location relative to the gene footprint",
        order=0,
    )


class VariantAssociationSummary(RowModel):
    trait_category: AssociationTrait
    trait: OntologyTerm
    num_variants: Union[int, Dict[str, int]]

    @field_serializer("trait_category")
    def serialize_trait_category(self, trait_category: AssociationTrait, _info):
        return str(AssociationTrait(trait_category))


class GeneticAssociationSummaryResponse(RecordResponse):
    data: List[VariantAssociationSummary]


class GeneticAssociationResponse(RecordResponse):
    data: Union[List[VariantAssociation], List[GeneVariantAssociation]]

    def to_vcf(self):
        raise NotImplementedError("VCF formatted responses coming soon.")

    def to_bed(self):
        raise NotImplementedError(
            "BED formatted responses not available for this type of data."
        )
