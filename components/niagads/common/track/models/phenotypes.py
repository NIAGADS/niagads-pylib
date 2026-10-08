import json
from typing import List, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.models import OntologyTermRecord
from pydantic import Field, field_serializer


class PhenotypeCount(CustomBaseModel):
    phenotype: Optional[list[str]] = None
    num_cases: int
    num_controls: Optional[int] = None

    def __str__(self):
        return self.to_info_string()

    @field_serializer("phenotype")
    def serialize_phenotype(self, phenotype: Optional[OntologyTermRecord], _info):
        return str(self.phenotype) if self.phenotype is not None else None


class Phenotype(CustomBaseModel):
    disease: Optional[List[OntologyTermRecord]] = Field(default=None, title="Disease")
    neuropathology: Optional[List[OntologyTermRecord]] = Field(
        default=None,
        title="Neuropathology",
        description="pathology or classification of the degree of pathology",
    )
    clinical_status: Optional[List[OntologyTermRecord]] = Field(
        default=None,
        title="Clinical Status or Symptom",
        description="observed or reported characteristic used to describe an individual's health state",
    )
    ethnicity: Optional[List[OntologyTermRecord]] = Field(
        default=None,
        title="Ethnicity",
        description="cultural or linguistic/national origin",
    )
    race: Optional[List[OntologyTermRecord]] = Field(
        default=None,
        title="Race",
        description="broad social/historyical classification, may be self-identified",
    )
    population: Optional[List[OntologyTermRecord]] = Field(
        default=None,
        title="Population",
        description="defined by genetic ancestry, geography, or shared evolutionary history (mapped to Human Ancestry Ontology)",
    )

    genotype: Optional[List[OntologyTermRecord]] = Field(default=None, title="Genotype")
    gender: Optional[List[OntologyTermRecord]] = Field(default=None, title="Gender")
    derived_phenotype: Optional[List[OntologyTermRecord]] = Field(
        default=None,
        title="Derived Phenotype",
        description="phenotype inferred or calculated from one or more measured phenotypic variables",
    )

    def get_ontology_terms(self) -> List[OntologyTermRecord]:
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
