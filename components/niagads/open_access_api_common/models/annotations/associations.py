from typing import List, Optional, Union
from niagads.common.models.ontology import OntologyTerm
from niagads.common.types import T_PubMedID
from niagads.database.schemas.dataset.composite_attributes import (
    BiosampleCharacteristics,
    Phenotype,
)
from niagads.open_access_api_common.models.core import RowModel
from niagads.open_access_api_common.models.features.variant import (
    VariantDisplayAnnotation,
    VariantFeature,
)
from niagads.open_access_api_common.models.response.core import RecordResponse
from pydantic import Field, model_validator


class AnnotatedVariantFeature(VariantFeature, VariantDisplayAnnotation):
    # for association tables
    pass


class VariantAssociation(RowModel):
    variant: AnnotatedVariantFeature = Field(title="Variant")
    test_allele: str = Field(title="Test Allele")
    track_id: Optional[str] = Field(default=None, title="Track ID")
    track_name: str = Field(
        title="Study",
        serialization_alias="study",
        description="NIAGADS Data Track or published study curated from the literature or a GWAS Catalog",
    )
    p_value: Union[float, str] = Field(title="p-Value")
    neg_log10_pvalue: float = Field(title="-log10pValue")
    subject_phenotypes: Optional[Phenotype] = Field(default=None, exclude=True)
    biosample_characterisitics: Optional[BiosampleCharacteristics] = Field(
        default=None, exclude=True
    )
    trait: OntologyTerm
    pubmed_id: Optional[List[T_PubMedID]]

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        obj["pubmed_id"] = self._list_to_string(self.pubmed_id, delimiter=delimiter)

        # promote the variant fields
        del obj["variant"]
        obj.update(self.variant._flat_dump())
        return obj

    @model_validator(mode="before")
    @classmethod
    def process_trait(cls, data: dict):
        """
        promote subject_phenotypes to get trait if trait is
        not already in the response
        """

        # this will happen b/c FastAPI tries all models
        # until it can successfully serialize
        if isinstance(data, str):
            return data

        # if not isinstance(data, dict):
        #     data = data.model_dump()  # assume data is an ORM w/model_dump mixin

        if "trait" in data:
            return data

        phenotypes: dict = data.get("subject_phenotypes")
        biosample: dict = data.get("biosample_characteristics")
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
    def get_model_fields(cls, asStr=False):
        fields = super().get_model_fields()

        del fields["subject_phenotypes"]
        del fields["variant"]
        fields.update(SimpleAnnotatedVariant.get_model_fields())

        return list(fields.keys()) if asStr else fields

    def table_fields(self, asStr=False, **kwargs):
        return super().table_fields(asStr, **kwargs)


class GeneVariantAssociation(VariantAssociation):
    relative_position: str


class GeneticAssociationResponse(RecordResponse):
    data: Union[List[VariantAssociation], List[GeneVariantAssociation]]

    def to_vcf(self):
        raise NotImplementedError("VCF formatted responses coming soon.")

    def to_bed(self):
        raise NotImplementedError(
            "BED formatted responses not available for this type of data."
        )
