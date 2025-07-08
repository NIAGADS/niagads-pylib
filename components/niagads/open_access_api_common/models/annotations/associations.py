from typing import List, Optional, Union
from niagads.common.models.ontology import OntologyTerm
from niagads.common.models.views.table import TableRow
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
    variant: AnnotatedVariantFeature = Field(title="Variant", order=1)
    test_allele: str = Field(title="Test Allele", order=2)
    p_value: Union[float, str] = Field(title="p-Value", order=3)

    trait: OntologyTerm = Field(title="Trait", description="associated trait", order=4)

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

        del fields["variant"]
        fields.update(AnnotatedVariantFeature.get_model_fields())

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

        return list(fields.keys()) if asStr else fields

    def table_fields(self, asStr=False, **kwargs):
        return super().table_fields(asStr, **kwargs)


class GeneVariantAssociation(VariantAssociation):
    relative_position: str = Field(
        title="Relative Position",
        description="location relative to the gene footprint",
        order=0,
    )


class GeneticAssociationResponse(RecordResponse):
    data: Union[List[VariantAssociation], List[GeneVariantAssociation]]

    def to_vcf(self):
        raise NotImplementedError("VCF formatted responses coming soon.")

    def to_bed(self):
        raise NotImplementedError(
            "BED formatted responses not available for this type of data."
        )
