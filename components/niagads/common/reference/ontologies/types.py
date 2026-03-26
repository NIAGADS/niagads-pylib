from enum import Enum
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.enums.core import CaseInsensitiveEnum


class RDFPropertyIRI(CaseInsensitiveEnum):
    """
    Enum for core RDF/OWL object property IRIs.
    """

    ENTITY_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class EntityTypeIRI(CaseInsensitiveEnum):
    """
    Enum for RDF/OWL ontology entity types

    """

    CLASS = "http://www.w3.org/2002/07/owl#Class"
    OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
    NAMED_INDIVIDUAL = "http://www.w3.org/2002/07/owl#NamedIndividual"
    ANNOTATION_PROPERTY = "http://www.w3.org/2002/07/owl#AnnotationProperty"

    def __str__(self):
        return self.name

    @classmethod
    def resolve_entity_type(cls, assigned_types: list[str]):
        """
        Resolves the entity type for a vertex.

        Args:
            assigned_types (list): list of assigned entity types for a vertex

        Returns:
            EntityIRI: The first matching EntityIRI for the assigned RDF type URIs.

        Raises:
            ValueError: If no RDF types are assigned to the entity, or if none match known entity types.
        """

        if not assigned_types:
            raise ValueError("No RDF type(s) assigned to entity.")
        for member in cls:
            if member.value in assigned_types:
                return member
        raise ValueError(f"Unrecognized ontology entity type(s): {assigned_types}")


class AnnotationPropertyIRI(CaseInsensitiveEnum):
    """
    Enum for annotation property IRIs used in ontology term metadata extraction.
    """

    EDITOR_PREFERRED_LABEL = "http://purl.obolibrary.org/obo/IAO_0000111"
    LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
    DEFINITION = "http://purl.obolibrary.org/obo/IAO_0000115"
    ID = "http://www.geneontology.org/formats/oboInOwl#id"
    HAS_EXACT_SYNONYM = "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"
    DEPRECATED = "http://www.w3.org/2002/07/owl#deprecated"
    COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"

    @classmethod
    def is_stored_property(cls, iri: str):
        """
        Checks if the given IRI is a valid member of the annotation property enum.

        Args:
            iri (str): The IRI to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            cls(iri)
            return True
        except ValueError:
            return False


class BiosampleType(Enum):
    TISSUE = OntologyTerm(
        term="tissue",
        curie="UBERON_0000479",
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
    CELL = OntologyTerm(
        term="cell",
        curie="CL:0000000",
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
        curie="EFO_0002660",
        term_irl="http://www.ebi.ac.uk/efo/EFO_0002660",
        ontology="Experimental Factor Ontology",
        defintion="A cell taken directly from a living organism, which is not immortalized.",
    )
    STEM_CELL = OntologyTerm(
        term="stem cell",
        curie="CL_0000034",
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
        curie="CL_0000001",
        term_iri="http://purl.obolibrary.org/obo/CL_0000001",
        ontology="Cell Ontology",
        defintion=(
            f"A cultured cell that is freshly isolated from a organismal source, "
            f"or derives in culture from such a cell prior to the culture being passaged. "
            f"Covers cells actively being cultured or stored in a quiescent state for future use."
        ),
    )

    EXPERIMENTALLY_MODIFIED_CELL = OntologyTerm(
        term="experimentally modified cell in vitro",
        curie="CL_0000578",
        term_iri="http://purl.obolibrary.org/obo/CL_0000578",
        ontology="Cell Ontology",
        definition=(
            f"A cell in vitro that has undergone physical changes "
            f"as a consequence of a deliberate and specific experimental procedure"
        ),
    )
    CELL_LINE = OntologyTerm(
        term="cell line",
        curie="CLO_0000031",
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
        curie="CLO_0037279",
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
        curie="CLO_0037307",
        term_iri="http://purl.obolibrary.org/obo/CLO_0037307",
        ontology="Cell Line Ontology",
        definition="A stem cell line cell that is pluripotent and is generated from an adult somatic cell.",
    )

    ORGANOID = OntologyTerm(
        term="organoid",
        curie="NCIT_C172259",
        term_iri="http://purl.obolibrary.org/obo/NCIT_C172259",
        ontology="NCIT",
        definition=(
            f"A three dimensional mass comprised of a cultured cell or "
            f"tissue sample that resembles an in vivo tissue or organ. "
            f"Organoids are grown in vitro from a combination of cells or "
            f"tissue fragments cultured in medium containing a variety of biochemical factors."
        ),
    )

    # adapted from https://stackoverflow.com/a/76131490
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

    @classmethod
    def list(cls):
        return [member.value.term for member in cls]
