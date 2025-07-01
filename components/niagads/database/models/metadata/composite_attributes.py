from typing import List, Optional, Set, Union

from niagads.common.constants.external_resources import ThirdPartyResources
from niagads.common.constants.ontologies import BiosampleType
from niagads.common.models.ontology import OntologyTerm
from niagads.common.types import T_PubMedID
from niagads.database.models.core import CompositeAttributeModel
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import dict_to_info_string, matches
from pydantic import (
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_serializer,
)


class ExperimentalDesign(CompositeAttributeModel):
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


class PhenotypeCount(CompositeAttributeModel):
    phenotype: Optional[OntologyTerm] = None
    num_cases: int
    num_controls: Optional[int] = None

    @field_serializer("phenotype")
    def serialize_phenotype(self, phenotype: Optional[OntologyTerm], _info):
        return str(self.phenotype) if self.phenotype is not None else None


class Phenotype(CompositeAttributeModel):
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

    @model_serializer()
    def serialize_model(self, listsAsStrings: bool = False):
        obj = {}
        for attr, value in self.__dict__.items():
            if value is not None:
                if attr == "study_diagnosis":
                    obj[attr] = [sd.model_dump() for sd in value]
                elif isinstance(value, list):
                    terms = [str(term) for term in value]
                    if listsAsStrings:
                        obj[attr] = "|".join(terms)
                    else:
                        obj[attr] = terms
                else:
                    obj[attr] = str(value)

        return obj


class BiosampleCharacteristics(CompositeAttributeModel):
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


# TODO: document provenance and file properties
class Provenance(CompositeAttributeModel):
    data_source: str = Field(
        title="Data Source", description="original file data source"
    )

    release_version: Optional[str] = None
    release_date: Optional[str] = None
    download_date: Optional[str] = None
    download_url: Optional[str] = None

    study: Optional[str] = None
    project: Optional[str] = None
    accession: Optional[str] = None  # really shouldn't be, but FILER

    pubmed_id: Optional[Set[T_PubMedID]] = None
    doi: Optional[Set[str]] = None

    consortium: Optional[Set[str]] = None
    attribution: Optional[str] = None

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
        dsKey = (
            self.data_source + "|" + self.data_source_version
            if self.data_source_version is not None
            else self.data_source
        )
        try:
            return ThirdPartyResources(dsKey).value
        except:
            raise ValueError(
                f"Data source URL not found for {dsKey}. Please add to external_resources.ThirdParty."
            )


class FileProperties(CompositeAttributeModel):
    file_name: Optional[str] = None
    url: Optional[str] = None
    md5sum: Optional[str] = Field(pattern=RegularExpressions.MD5SUM, default=None)

    bp_covered: Optional[int] = None
    num_intervals: Optional[int] = None
    file_size: Optional[int] = None

    file_format: Optional[str] = None
    file_schema: Optional[str] = None
    release_date: Optional[str] = None
