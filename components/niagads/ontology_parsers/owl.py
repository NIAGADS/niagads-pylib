from typing import Iterator

from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.helpers import get_field_iri
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.reference.ontologies.types import (
    AnnotationPropertyIRI,
    EntityTypeIRI,
    RDFPropertyIRI,
)
from rdflib import BNode, Graph, Literal, URIRef


class OWLParser(ComponentBaseMixin):
    def __init__(
        self, owl_file: str, logger=None, debug: bool = False, verbose: bool = False
    ):
        super().__init__(debug=debug, verbose=verbose)
        if logger is not None:
            self.logger = logger
        self._graph = Graph()
        if self._verbose:
            self.logger.info("Parsing Ontology Graph")
        self._graph.parse(owl_file, format="xml")

    def __resolve_entity_type(self, node) -> EntityTypeIRI:
        assigned_types = [
            str(obj)
            for obj in self._graph.objects(
                node, URIRef(str(RDFPropertyIRI.ENTITY_TYPE))
            )
        ]
        return EntityTypeIRI.resolve_entity_type(assigned_types)

    def __get_term_value(
        self, entity_properties: dict, curie: str, is_deprecated: bool
    ) -> str:

        # get label, checking preferred first
        term = entity_properties.get(get_field_iri("label", preferred=True), [None])[0]
        if term is None:  # no editor preffered label
            term = entity_properties.get(
                get_field_iri("label", preferred=False), [None]
            )[0]

        if term is None:
            term = entity_properties.get(get_field_iri("comment"), [None])[0]

        # if still no term, then entity has no label, extract from curie
        # (expecting property, e.g., oboInOwl#saved-by - where label = 'saved-by')
        if term is None and "#" in curie:
            term = curie.split("#")[1]

        if term is None:
            if is_deprecated:  # sometimes no label is provided for deprecated CURIEs
                return None
            else:  # still none?
                raise ValueError(
                    f"Cannot extract term from entity: {entity_properties}"
                )
        return term

    def __build_ontology_term(
        self, entity_iri, entity_type: EntityTypeIRI, entity_properties: dict
    ):
        if not entity_properties:
            # not a labelled term or validly annotated term
            return None

        curie = entity_properties.get(get_field_iri("curie"), [None])[0]
        if curie is None:  # then extract from iri, e.g, for AnnotationProperty
            curie = OntologyTerm.extract_curie(entity_iri)
        is_deprecated = bool(
            entity_properties.get(get_field_iri("is_deprecated"), [False])[0]
        )
        term = self.__get_term_value(entity_properties, curie, is_deprecated)
        if term is None:
            return None

        definition = entity_properties.get(get_field_iri("definition"), [None])[0]
        synonyms = entity_properties.get(get_field_iri("synonym"), None)

        return {
            "term_iri": entity_iri,
            "entity_type": str(entity_type),
            "curie": curie,
            "term": term,
            "definition": definition,
            "synonyms": synonyms,
            "is_deprecated": is_deprecated,
        }

    def extract_terms(self) -> Iterator[dict]:
        """
        Extracts ontology term entities from the RDF graph.

        Iterates over all subjects in the RDF graph, resolves their entity type,
        and collects annotation properties. Yields a dictionary for each term
        with its IRI, type, and properties (label, definition, synonyms, etc.).

        Returns:
            Iterator[dict]: dict with fields that can be used to build OntologyTerm
                or OntologyTermVertex object as required by Plugin
        """
        for subject in self._graph.subjects():
            subject_iri = str(subject)

            try:
                subject_type: EntityTypeIRI = self.__resolve_entity_type(subject)
            except ValueError:
                continue  # skip the node

            subject_properties = {}
            for predicate, obj in self._graph.predicate_objects(subject):
                predicate_iri = str(predicate)
                object_iri = str(obj)

                if isinstance(obj, Literal):
                    if AnnotationPropertyIRI.is_stored_property(predicate_iri):
                        subject_properties.setdefault(predicate_iri, []).append(
                            object_iri
                        )

            ontology_term = self.__build_ontology_term(
                subject_iri, subject_type, subject_properties
            )
            if ontology_term is not None:
                yield ontology_term
            else:
                if self._verbose:
                    self.logger.warning(f"Skipped deprecated term: {subject_iri}")

    def extract_triples(self) -> Iterator[dict]:
        """
        Extracts ontology relationship triples from the RDF graph.

        Iterates over all subjects and their predicate-object pairs in the RDF graph.
        For each predicate that is an object property or entity type, yields a Triple
        object with subject, predicate, and object IRIs. Skips annotation properties
        and unsupported predicate types.

        Returns:
            Iterator[Triple]: Each Triple contains subject, predicate, and object IRIs.
        """
        for subject in self._graph.subjects():
            subject_iri = str(subject)

            try:
                self.__resolve_entity_type(subject)
            except ValueError:
                continue  # skip the node

            for predicate, obj in self._graph.predicate_objects(subject):
                predicate_iri = str(predicate)
                object_iri = str(obj)

                if isinstance(obj, URIRef):  # relation prop
                    # get the type of the predicate
                    try:
                        predicate_type = self.__resolve_entity_type(predicate)
                    except ValueError:
                        continue  # not a supported predicate type

                    # only keep triples that are not annotations
                    if (
                        predicate_type == EntityTypeIRI.OBJECT_PROPERTY
                        or predicate_iri == RDFPropertyIRI.ENTITY_TYPE
                    ):
                        yield {
                            subject: subject_iri,
                            predicate: predicate_iri,
                            object: object_iri,
                        }

    def extract_restrictions(self):
        raise NotImplementedError()
        for subject in self._graph.subjects():
            subject_iri = str(subject)

            try:
                self.__resolve_entity_type(subject)
            except ValueError:
                continue  # skip the node

            subject_properties = {}
            for predicate, obj in self._graph.predicate_objects(subject):
                predicate_iri = str(predicate)
                object_iri = str(obj)

                if isinstance(obj, BNode):
                    continue
                    # Check if this BNode is an OWL restriction
                    # if (obj, RDF.type, OWL.Restriction) in self._graph:
                    #   ..
