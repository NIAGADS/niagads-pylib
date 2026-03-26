"""
Ontology helper functions for mapping OntologyTerm fields to property IRIs.

This module provides utilities for working with ontology field/property mappings,
especially for use in ETL and graph schema construction.
"""

from niagads.common.reference.ontologies.types import AnnotationPropertyIRI


def get_field_iri(field: str, preferred=True) -> str:
    """
    Get the property IRI(s) used to retrieve values of an OntologyTerm object field.

    Args:
        field (str): The OntologyTerm field name (e.g., 'term', 'definition', 'term_id', 'synonym', 'is_deprecated').
        preferred (bool, optional): If True, use the preferred label IRI for 'term'. Defaults to True.

    Returns:
        str: The property IRI corresponding to the requested field.

    Raises:
        ValueError: If the field does not have a property IRI mapping.
    """

    match field:
        case "label":
            if preferred:
                return AnnotationPropertyIRI.EDITOR_PREFERRED_LABEL
            else:
                return AnnotationPropertyIRI.LABEL
        case "definition":
            return AnnotationPropertyIRI.DEFINITION
        case "curie":
            return AnnotationPropertyIRI.ID
        case "synonym":
            return AnnotationPropertyIRI.HAS_EXACT_SYNONYM
        case "is_deprecated":
            return AnnotationPropertyIRI.DEPRECATED
        case "comment":
            return AnnotationPropertyIRI.COMMENT
        case _:
            raise ValueError(f"No property IRI mapping required for '{field}'.")
