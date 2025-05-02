from datetime import date
from enum import Enum, auto
from typing import List, Optional, Set

from niagads.common.constants.external_resources import ThirdPartyResources
from niagads.common.core import NullFreeModel
from niagads.common.models.core import OntologyTerm
from niagads.common.types.core import T_DOI, T_PubMedID
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import Field, computed_field, field_validator


class TrackDataStore(CaseInsensitiveEnum):
    GENOMICS = auto()
    FILER = auto()
    SHARED = auto()


class ExperimentalDesign(NullFreeModel):
    antibody_target: Optional[str] = None
    assay: Optional[str] = None
    analysis: Optional[str] = None
    classification: Optional[str] = None
    data_category: Optional[str] = None
    output_type: Optional[str] = None
    is_lifted: Optional[bool] = False
    covariates: Optional[List[str]] = None


class Phenotype(NullFreeModel):
    disease: Optional[List[str]] = None
    ethnicity: Optional[List[str]] = None
    race: Optional[List[str]] = None
    neuropathology: Optional[List[str]] = None


class BiosampleType(Enum):
    CELL_LINE = OntologyTerm(
        term="cell line",
        term_id="CLO_0000031",
        term_iri="http://purl.obolibrary.org/obo/CLO_0000031",
        ontology="Cell Line Ontology",
        definition=(
            f"A cultured cell population that represents a "
            f"genetically stable and homogenous population of "
            f"cultured cells that shares a common propagation "
            f"history."
        ),
    )
    CELL = OntologyTerm(
        term="cell",
        term_id="CL:0000000",
        term_iri="http://purl.obolibrary.org/obo/CL_0000000",
        ontology="Cell Ontology",
        defintion=(
            f"A material entity of anatomical origin "
            f"(part of or deriving from an organism) that "
            f"has as its parts a maximally connected cell "
            f"compartment surrounded by a plasma membrane.)"
        ),
    )
    PRIMARY_CELL = OntologyTerm(
        term="primary cell",
        term_id="EFO_0002660",
        term_irl="http://www.ebi.ac.uk/efo/EFO_0002660",
        ontology="Experimental Factor Ontology",
        defintion="A cell taken directly from a living organism, which is not immortalized.",
    )
    TISSUE = OntologyTerm(
        term="tissue",
        term_id="UBERON_0000479",
        term_iri="http://purl.obolibrary.org/obo/UBERON_0000479",
        ontology="UBERON",
        definition=(
            f"Multicellular anatomical structure that consists "
            f"of many cells of one or a few types, arranged in an "
            f"extracellular matrix such that their long-range "
            f"organisation is at least partly a repetition of their "
            f"short-range organisation.",
        ),
    )

    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str):  # allow to be case insensitive
        try:
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
        except ValueError as err:
            raise err


class BiosampleCharacteristics(NullFreeModel):
    system: Optional[List[str]] = None
    tissue: Optional[List[str]] = None
    biomarker: Optional[List[str]] = None
    biosample_type: BiosampleType
    biosample: Optional[List[OntologyTerm]] = Field(
        default=None, description="ontology term/id pairs describing the biosample"
    )

    life_stage: Optional[str] = Field(
        default=None, description="donor/sample life stage: adult, fetal, embryo"
    )


class Provenance(NullFreeModel):
    data_source: str

    release_version: Optional[str] = None
    release_date: Optional[date] = None
    download_date: Optional[date] = None
    download_url: Optional[str] = None

    study: Optional[str] = None
    project: Optional[str] = None
    accession: Optional[str] = None  # really shouldn't be, but FILER

    pubmed_id: Optional[Set[T_PubMedID]] = None
    doi: Optional[Set[str]] = None

    consortia: Optional[List[str]] = None
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


class FileProperties(NullFreeModel):
    file_name: Optional[str] = None
    url: Optional[str] = None
    md5sum: Optional[str] = Field(pattern=RegularExpressions.MD5SUM, default=None)

    bp_covered: Optional[int] = None
    num_intervals: Optional[int] = None
    file_size: Optional[int] = None

    file_format: Optional[str] = None
    file_schema: Optional[str] = None
    release_date: Optional[date] = None
