import json
from typing import List, Optional

from niagads.common.models.core import TransformableModel
from niagads.common.models.ontologies import OntologyTerm
from pydantic import Field, field_serializer


class PhenotypeCount(TransformableModel):
    phenotype: Optional[OntologyTerm] = None
    num_cases: int
    num_controls: Optional[int] = None

    def __str__(self):
        return self.as_info_string()

    @field_serializer("phenotype")
    def serialize_phenotype(self, phenotype: Optional[OntologyTerm], _info):
        return str(self.phenotype) if self.phenotype is not None else None


class Phenotype(TransformableModel):
    disease: Optional[List[OntologyTerm]] = Field(default=None, title="Disease")
    neuropathology: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Neuropathology",
        description="pathology or classification of the degree of pathology",
    )
    ethnicity: Optional[List[OntologyTerm]] = Field(default=None, title="Ethnicity")
    race: Optional[List[OntologyTerm]] = Field(default=None, title="Race")

    genotype: Optional[List[OntologyTerm]] = Field(default=None, title="Genotype")
    gender: Optional[List[OntologyTerm]] = Field(default=None, title="Gender")
    study_diagnosis: Optional[List[PhenotypeCount]] = Field(
        default=None,
        title="Study Diagnosis",
        description="number of cases and controls",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = {
            k: self._list_to_string(v, delimiter=delimiter)
            for k, v in super()._flat_dump(null_free=nullFree)
        }
        return obj

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

    def as_table_row(self, **kwargs):
        row = super().as_table_row(**kwargs)
        if self.study_diagnosis is not None:
            row.update(
                "study_diagnosis",
                {"value": json.dumps([d.model_dump() for d in self.study_diagnosis])},
            )
