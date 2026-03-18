import json
from typing import List, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.models import OntologyTerm
from pydantic import Field, field_serializer


class PhenotypeCount(CustomBaseModel):
    phenotype: Optional[OntologyTerm] = None
    num_cases: int
    num_controls: Optional[int] = None

    def __str__(self):
        return self.as_info_string()

    @field_serializer("phenotype")
    def serialize_phenotype(self, phenotype: Optional[OntologyTerm], _info):
        return str(self.phenotype) if self.phenotype is not None else None


class Phenotype(CustomBaseModel):
    disease: Optional[List[OntologyTerm]] = Field(default=None, title="Disease")
    neuropathology: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Neuropathology",
        description="pathology or classification of the degree of pathology",
    )
    ethnicity: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Ethnicity",
        description="cultural or linguistic/national origin",
    )
    race: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Race",
        description="broad social/historyical classification, may be self-identified",
    )
    population: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Population",
        description="defined by genetic ancestry, geography, or shared evolutionary history (mapped to Human Ancestry Ontology)",
    )

    genotype: Optional[List[OntologyTerm]] = Field(default=None, title="Genotype")
    gender: Optional[List[OntologyTerm]] = Field(default=None, title="Gender")

    def get_ontology_terms(self) -> List[OntologyTerm]:
        """Extract all ontology terms from phenotype fields.

        Iterates over all model fields and collects OntologyTerm instances
        from list fields.

        Returns:
            List of OntologyTerm objects from all phenotype categories.
        """
        terms = []
        for field_name in self.__class__.model_fields.keys():
            if field_name == "study_diagnosis":
                continue
            field_value = getattr(self, field_name, None)
            if field_value and isinstance(field_value, list):
                terms.extend(field_value)
        return terms
