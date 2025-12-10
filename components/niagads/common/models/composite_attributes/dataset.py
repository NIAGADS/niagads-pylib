import json
from typing import List, Optional, Set, Union

from niagads.common.constants.external_resources import (
    NIAGADSResources,
    ThirdPartyResources,
)
from niagads.common.constants.ontologies import BiosampleType
from niagads.common.models.core import TransformableModel
from niagads.common.models.ontology import OntologyTerm
from niagads.common.types import T_PubMedID
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import (
    Field,
    computed_field,
    field_serializer,
    field_validator,
)


class ExperimentalDesign(TransformableModel):
    antibody_target: Optional[str] = Field(default=None, title="Antibody Target")
    assay: Optional[str] = Field(default=None, title="Assay")
    analysis: Optional[str] = Field(default=None, title="Analysis")
    classification: Optional[str] = Field(default=None, title="Classification")
    data_category: Optional[str] = Field(default=None, title="Data Category")
    output_type: Optional[str] = Field(default=None, title="Output Type")
    is_lifted: Optional[bool] = Field(
        default=None,
        title="Is Lifted?",
        description="data are lifted from earlier genome build",
    )
    covariates: Optional[List[str]] = Field(default=None, title="Covariates")

    def __str__(self):
        return self.as_info_string()

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)
        if self.covariates is not None:
            obj["covarites"] = self._list_to_string(
                self.covariates, delimiter=delimiter
            )
        return obj


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
    ethnicity: Optional[List[OntologyTerm]] = Field(default=None, title="Ethnicity")
    race: Optional[List[OntologyTerm]] = Field(default=None, title="Race")
    neuropathology: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Neuropathology",
        description="pathology or classification of the degree of pathology",
    )
    genotype: Optional[List[OntologyTerm]] = Field(
        default=None, title="APOE Allele or Carrier Status"
    )
    biological_sex: Optional[List[OntologyTerm]] = Field(
        default=None, title="Biological Sex"
    )
    study_diagnosis: Optional[List[PhenotypeCount]] = Field(
        default=None,
        title="Study Diagnosis",
        description="number of cases and controls",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = {
            k: self._list_to_string(v, delimiter=delimiter)
            for k, v in super()._flat_dump(nullFree=nullFree)
        }
        return obj

    def as_table_row(self, **kwargs):
        row = super().as_table_row(**kwargs)
        if self.study_diagnosis is not None:
            row.update(
                "study_diagnosis",
                {"value": json.dumps([d.model_dump() for d in self.study_diagnosis])},
            )


class BiosampleCharacteristics(TransformableModel):
    system: Optional[List[str]] = Field(
        default=None, title="Biosample: Anatomical System"
    )
    tissue: Optional[List[str]] = Field(default=None, title="Biosample: Tissue")
    biomarker: Optional[List[str]] = Field(default=None, title="Biomarker")
    biosample_type: Optional[Union[BiosampleType, str]] = Field(
        default=None, title="Biosample Type"
    )
    biosample: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Biosample",
        description="ontology term/id pairs describing the biosample",
    )

    life_stage: Optional[str] = Field(
        default=None,
        title="Biosample: Life Stage",
        description="donor or sample life stage",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = {
            k: (
                self._list_to_string(v, delimiter=delimiter)
                if isinstance(v, list) and k != "biosample"
                else v
            )
            for k, v in super()._flat_dump(nullFree=nullFree).items()
        }
        if self.biosample is not None:
            # have to redo b/c its been serialized above
            obj["biosample"] = self._list_to_string(self.biosample, delimiter=delimiter)

        return obj


# TODO: document provenance and file properties
class Provenance(TransformableModel):
    data_source: str = Field(
        title="Data Source", description="original file data source"
    )

    release_version: Optional[str] = None
    release_date: Optional[str] = None
    download_date: Optional[str] = None
    download_url: Optional[str] = None  # Field(exclude=True)

    study: Optional[str] = None
    project: Optional[str] = None
    accession: Optional[str] = None  # really shouldn't be optional, but FILER

    pubmed_id: Optional[Set[T_PubMedID]] = None
    doi: Optional[Set[str]] = None

    consortium: Optional[Set[str]] = None
    attribution: Optional[str] = None

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = {
            k: (
                self._list_to_string(list(v), delimiter=delimiter)
                if isinstance(v, set)
                else str(v) if v is not None else v
            )
            for k, v in super()._flat_dump(nullFree=nullFree).items()
        }
        return obj

    @field_validator("doi", mode="after")
    def validate_doi(cls, values: Set[str]):
        """create validator b/c Pydantic does not support patterns w/lookaheads"""
        if values is not None and len(values) > 0:
            for v in values:
                if not matches(RegularExpressions.DOI, v):
                    raise ValueError(
                        f"Invalid DOI format: {v}. Please provide a valid DOI."
                    )
        return values

    @computed_field
    @property
    def data_source_url(self) -> str:
        # dsKey: str = (
        #    f"{self.data_source}|{self.release_version}"
        #    if self.release_version is not None
        #    else self.data_source
        # )
        # removed versioning from the data source URLs; incorrect legacy from FILER
        dsKey = self.data_source
        try:
            return ThirdPartyResources(dsKey).value
        except:
            try:
                return NIAGADSResources(dsKey).value
            except:
                raise ValueError(
                    f"Data source URL not found for {dsKey}. Please add to external_resources.ThirdParty."
                )


class FileProperties(TransformableModel):
    file_name: Optional[str] = None
    url: Optional[str] = None
    md5sum: Optional[str] = Field(pattern=RegularExpressions.MD5SUM, default=None)

    bp_covered: Optional[int] = None
    num_intervals: Optional[int] = None
    file_size: Optional[int] = None

    file_format: Optional[str] = None
    file_schema: Optional[str] = None
    release_date: Optional[str] = None  # Field(exclude=True)
