from typing import Iterator

from niagads.common.core import ComponentBaseMixin
from niagads.ontologies.helpers import get_field_iri
from niagads.ontologies.types import (
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
        self.logger.info("Initializing parser")
        self._graph.parse(owl_file, format="xml")

    def __resolve_entity_type(self, node) -> EntityTypeIRI:
        assigned_types = [
            str(obj)
            for obj in self._graph.objects(
                node, URIRef(str(RDFPropertyIRI.ENTITY_TYPE))
            )
        ]
        return EntityTypeIRI.resolve_entity_type(assigned_types)

    def __build_term(
        self, entity_iri, entity_type: EntityTypeIRI, entity_properties: dict
    ):
        label = entity_properties.get(get_field_iri("term", preferred=True), [None])[0]
        if label is None:  # no editor preffered label
            label = entity_properties.get(
                get_field_iri("term", preferred=False), [None]
            )[0]

        term_id = entity_properties.get(get_field_iri("term_id"), [None])[0]
        definition = entity_properties.get(get_field_iri("definition"), [None])[0]
        synonyms = entity_properties.get(get_field_iri("synonym"), [])
        is_deprecated = bool(
            entity_properties.get(get_field_iri("is_deprecated"), [False])[0]
        )

        return {
            "term_iri": entity_iri,
            "entity_type": str(entity_type),
            "curie": term_id,
            "term": label,
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

            yield self.__build_term(subject_iri, subject_type, subject_properties)

    def extract_triples(self) -> Iterator[Triple]:
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
