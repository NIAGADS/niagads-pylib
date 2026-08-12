"""
Basic parsing of MeSH N-Triples to extract Topical Descriptor and Concept level terms
for dataset annotation.  To leverage MeSH for additional search
it probably would be best to store as graph w/combination indexing table that includes
the tree numbers (represented as an LTRee, if sticking to postgres).
See https://www.nlm.nih.gov/mesh/intro_retrieval.html

i.e., now just retrieving topical descriptors, preferred terms, and preferred concepts
so can translate into ontology terms and synonyms
"""

from typing import Generator, Iterator, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.rdf_parsers.rdf import NTriplesParser
from pydantic import Field
from rdflib import RDF, RDFS, URIRef

MeSHV = "http://id.nlm.nih.gov/mesh/vocab#"


class MeSHBaseElement(CustomBaseModel):
    iri: str
    id: str
    label: str
    is_active: str


class MeSHTerm(MeSHBaseElement):
    abbreviation: Optional[str] = None
    alt_labels: Optional[list[str]] = None


class MeSHConcept(MeSHBaseElement):
    preferred_term: MeSHTerm
    scope_note: Optional[str] = None
    terms: Optional[list[MeSHTerm]] = None


class MeSHDescriptor(MeSHBaseElement):
    is_active: bool
    preferred_concept: MeSHConcept
    # concepts: Optional[list[MeSHConcept]] = None


class MeSHParser(NTriplesParser):
    def __init__(
        self,
        file: str,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):

        super().__init__(
            file=file,
            namespace=MeSHV,
            logger=logger,
            debug=debug,
            verbose=verbose,
        )

    # self._namespace.TopicalDescriptor
    def extract_topical_descriptors(
        self,
    ) -> Iterator[MeSHDescriptor]:
        for descriptor in self._graph.subjects(
            RDF.type, self._namespace.TopicalDescriptor
        ):
            preferred_concept = self.get_value(
                subject=descriptor, predicate=self._namespace.preferredConcept
            )

            yield MeSHDescriptor(
                iri=str(descriptor),
                id=self.get_value(
                    subject=descriptor,
                    predicate=self._namespace.identifier,
                    as_string=True,
                ),
                label=self.get_value(
                    subject=descriptor, predicate=RDFS.label, as_string=True
                ),
                is_active=self.get_value(
                    subject=descriptor, predicate=self._namespace.active, as_string=True
                ),
                preferred_concept=self.extract_concept(preferred_concept),
            )

    def _get_linked_terms(self, object: URIRef) -> Generator:
        return self._graph.objects(subject=object, predicate=self._namespace.terms)

    def extract_term(self, term: URIRef):
        preferred_label = self.get_value(
            subject=term, predicate=self._namespace.prefLabel, as_string=True
        )
        label = self.get_value(subject=term, predicate=RDFS.label, as_string=True)
        alt_labels = [
            str(alt_label)
            for alt_label in self._graph.objects(term, self._namespace.altLabel)
        ]

        # if preferred label is not none and label is not the preferred label,
        # # then preferred label = label, label gets appended to alt_labels
        if preferred_label is not None and preferred_label != label:
            if label not in alt_labels:
                alt_labels.append(label)
            label = preferred_label

        return MeSHTerm(
            iri=str(term),
            id=self.get_value(
                subject=term, predicate=self._namespace.identifier, as_string=True
            ),
            label=label,
            is_active=self.get_value(
                subject=term, predicate=self._namespace.active, as_string=True
            ),
            alt_labels=alt_labels,
            abbreviation=self.get_value(
                subject=term, predicate=self._namespace.abbreviation, as_string=True
            ),
        )

    def extract_concept(self, concept: URIRef):
        preferred_term = self.get_value(
            subject=concept, predicate=self._namespace.preferredTerm
        )
        return MeSHConcept(
            iri=str(concept),
            id=self.get_value(
                subject=concept, predicate=self._namespace.identifier, as_string=True
            ),
            label=self.get_value(subject=concept, predicate=RDFS.label, as_string=True),
            is_active=self.get_value(
                subject=concept, predicate=self._namespace.active, as_string=True
            ),
            scope_note=self.get_value(
                subject=concept, predicate=self._namespace.scopeNote, as_string=True
            ),
            preferred_term=self.extract_term(preferred_term),
            terms=[self.extract_term(term) for term in self._get_linked_terms(concept)],
        )

    def extract_concepts(self) -> Iterator[MeSHConcept]:
        for concept in self._graph.subjects(RDF.type, self._namespace.Concept):
            yield self.extract_concept(concept)
