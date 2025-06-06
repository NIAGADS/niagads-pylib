from enum import Enum, auto
from typing import List, Optional, Set, Union

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


class StudyDiagnosis(CaseInsensitiveEnum):
    CASE = auto()
    CONTROL = auto()
    OTHER = auto()


class Phenotype(NullFreeModel):
    disease: Optional[List[str]] = Field(default=None, title="Disease")
    ethnicity: Optional[List[str]] = Field(default=None, title="Ethnicity")
    race: Optional[List[str]] = Field(default=None, title="Race")
    neuropathology: Optional[List[str]] = Field(default=None, title="Neuropathology")
    study_diagnosis: Optional[StudyDiagnosis] = Field(
        default=None,
        title="Study Diagnosis",
        description="status of individual in the study as a case or control",
    )


class BiosampleType(Enum):
    EXPERIMENTALLY_MODIFIED_CELL = OntologyTerm(
        term="experimentally modified cell in vitro",
        term_id="CL_0000578",
        term_iri="http://purl.obolibrary.org/obo/CL_0000578",
        ontology="Cell Ontology",
        definition=(
            f"A cell in vitro that has undergone physical changes "
            f"as a consequence of a deliberate and specific experimental procedure"
        ),
    )
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
    ESC_CELL_LINE = OntologyTerm(
        term="embryonic stem cell line cell",
        term_id="CLO_0037279",
        term_iri="http://purl.obolibrary.org/obo/CLO_0037279",
        ontology="Cell Line Ontology",
        definition=(
            f"A stem cell line cell that is dervied from an embryotic stem cell, "
            f" a pluripotent stem cell derived from the inner cell mass "
            f"of a blastocyst, an early-stage perimplantation embryo."
        ),
    )
    IPSC_CELL_LINE = OntologyTerm(
        term="induced pluripotent stem cell line cell",
        term_id="CLO_0037307",
        term_iri="http://purl.obolibrary.org/obo/CLO_0037307",
        ontology="Cell Line Ontology",
        definition="A stem cell line cell that is pluripotent and is generated from an adult somatic cell.",
    )
    CELL = OntologyTerm(
        term="cell",
        term_id="CL:0000000",
        term_iri="http://purl.obolibrary.org/obo/CL_0000000",
        ontology="Cell Ontology",
        definition=(
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
    STEM_CELL = OntologyTerm(
        term="stem cell",
        term_id="CL_0000034",
        term_iri="http://purl.obolibrary.org/obo/CL_0000034",
        ontology="Cell Ontology",
        definition=(
            f"A relatively undifferentiated cell that retains the ability to divide "
            f"and proliferate throughout life to provide progenitor "
            f"cells that can differentiate into specialized cells."
        ),
    )
    PRIMARY_CULTURE = OntologyTerm(
        term="primary cell culture",
        term_id="CL_0000001",
        term_iri="http://purl.obolibrary.org/obo/CL_0000001",
        ontology="Cell Ontology",
        defintion=(
            f"A cultured cell that is freshly isolated from a organismal source, "
            f"or derives in culture from such a cell prior to the culture being passaged. "
            f"Covers cells actively being cultured or stored in a quiescent state for future use."
        ),
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
            f"short-range organisation."
        ),
    )
    ORGANOID = OntologyTerm(
        term="organoid",
        term_id="NCIT_C172259",
        term_iri="http://purl.obolibrary.org/obo/NCIT_C172259",
        ontology="NCIT",
        definition=(
            f"A three dimensional mass comprised of a cultured cell or "
            f"tissue sample that resembles an in vivo tissue or organ. "
            f"Organoids are grown in vitro from a combination of cells or "
            f"tissue fragments cultured in medium containing a variety of biochemical factors."
        ),
    )

    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str):  # allow to be case insensitive
        try:
            lvalue = value.lower()

            for member in cls:
                if member.name.lower() == lvalue.replace(" ", "_"):
                    return member

            if lvalue == "primary tissue":
                return cls.TISSUE
            if lvalue == "in vitro differentiated cells":
                return cls.EXPERIMENTALLY_MODIFIED_CELL
            if lvalue == "induced pluripotent stem cell line" or "ipsc" in lvalue:
                return cls.IPSC_CELL_LINE
            if lvalue == "esc derived":
                return cls.ESC_CELL_LINE
            if lvalue == "immortalized cell line":
                return cls.CELL_LINE
            if lvalue == "cell type":
                return cls.CELL

        except ValueError as err:
            raise err

    def __str__(self):
        return self.value.term


class BiosampleCharacteristics(NullFreeModel):
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
class Provenance(NullFreeModel):
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

    consortia: Optional[List[str]] = None
    attribution: Optional[str] = None

    @field_validator("doi", mode="after")
    def valistr_doi(cls, values: Set[str]):
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
    release_date: Optional[str] = None
