"""Parse MeSH N-Triples into descriptors, concepts, and terms.

The parser extracts topical descriptors, preferred terms, preferred concepts,
and synonyms for dataset annotation. To leverage MeSH for additional search,
it would probably be best to store it as a graph with a combination indexing
table that includes the tree numbers (represented as an ltree when using
PostgreSQL). See the MeSH retrieval documentation for background:
https://www.nlm.nih.gov/mesh/intro_retrieval.html.

For now, this module retrieves topical descriptors, preferred terms, and
preferred concepts so they can be translated into ontology terms and synonyms;
tree strings and other relationships are not currently extracted.
"""

from typing import Generator, Iterator, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.rdf_parsers.rdf import NTriplesParser
from rdflib import RDF, RDFS, Literal, URIRef
from rdflib.exceptions import UniquenessError

MeSHV = "http://id.nlm.nih.gov/mesh/vocab#"


class MeSHBaseElement(CustomBaseModel):
    """Common fields shared by MeSH descriptors, concepts, and terms.

    Attributes:
        iri: The element's IRI in the MeSH vocabulary.
        id: The MeSH identifier.
        label: The element's display label.
        is_active: Whether the element is active in MeSH.
    """

    iri: str
    id: str
    label: str
    is_active: str


class MeSHTerm(MeSHBaseElement):
    """A MeSH term and its optional abbreviation and alternate labels.

    Attributes:
        abbreviation: The term's abbreviation, when one is defined.
        alt_labels: Alternate labels associated with the term.
    """

    abbreviation: Optional[str] = None
    alt_labels: Optional[list[str]] = None


class MeSHConcept(MeSHBaseElement):
    """A MeSH concept with its preferred term and related terms.

    Attributes:
        preferred_term: The concept's preferred term.
        scope_note: A note describing the scope of the concept.
        terms: Terms associated with the concept.
    """

    preferred_term: MeSHTerm
    scope_note: Optional[str] = None
    terms: Optional[list[MeSHTerm]] = None


class MeSHDescriptor(MeSHBaseElement):
    """A MeSH topical descriptor and its preferred concept.

    Attributes:
        is_active: Whether the descriptor is active in MeSH.
        preferred_concept: The descriptor's preferred concept.
    """

    is_active: bool
    preferred_concept: MeSHConcept
    # concepts: Optional[list[MeSHConcept]] = None


class MeSHParser(NTriplesParser):
    """Extract MeSH entities from an N-Triples RDF graph."""

    def __init__(
        self,
        file: str,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """Initialize a parser for a MeSH N-Triples file.

        Args:
            file: Path to the MeSH N-Triples file.
            logger: Optional logger used for parser messages.
            debug: If True, enable debug mode.
            verbose: If True, enable verbose logging.
        """

        super().__init__(
            file=file,
            namespace=MeSHV,
            logger=logger,
            debug=debug,
            verbose=verbose,
        )

    def extract_topical_descriptors(
        self,
    ) -> Iterator[MeSHDescriptor]:
        """Yield topical descriptors from the MeSH graph.

        Returns:
            Iterator[MeSHDescriptor]: Topical descriptors, including each
                descriptor's preferred concept.
        """
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
                label=self._get_label(descriptor),
                is_active=self.get_value(
                    subject=descriptor,
                    predicate=self._namespace.active,
                    default=True,
                    as_string=True,
                ),
                preferred_concept=self.extract_concept(preferred_concept),
            )

    def _get_linked_terms(self, subject: URIRef) -> Generator:
        """Return terms linked to a MeSH concept.

        Args:
            object: IRI of the concept whose linked terms should be returned.

        Returns:
            Generator: Term IRIs linked through the MeSH ``terms`` predicate.
        """
        # note have to use bracket notation b/c namespace.term is a class method that is
        # in fact, equivalent to the dot or bracket notation, i.e., self._namespace.term('term')
        # == self._namespace['term'].  Cannot use dot notation due to the name collision
        return self._graph.objects(subject=subject, predicate=self._namespace["term"])

    def _get_label(self, subject: URIRef):
        try:
            label = self.get_value(
                subject=subject, predicate=RDFS.label, as_string=True
            )
        except UniquenessError:
            # if there are multiple labels, they are distinguished by language
            # get the English label
            label = next(
                (
                    str(label)
                    for label in self._graph.objects(subject, RDFS.label)
                    if isinstance(label, Literal) and label.language == "en"
                ),
                None,
            )

        return label

    def extract_term(self, term: URIRef):
        """Extract a MeSH term from the graph.

        Preferred labels replace the regular label when both are present. The
        replaced label is retained as an alternate label when necessary.

        Args:
            term: IRI of the MeSH term to extract.

        Returns:
            MeSHTerm: A populated MeSH term model.
        """
        preferred_label = self.get_value(
            subject=term, predicate=self._namespace.prefLabel, as_string=True
        )

        label = self._get_label(term)

        alt_labels = [
            str(alt_label)
            for alt_label in self._graph.objects(term, self._namespace.altLabel)
        ]

        # if preferred label is not none and label is not the preferred label,
        # # then preferred label = label, label gets appended to alt_labels
        if preferred_label is not None and preferred_label != label:
            if label is not None:
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
                subject=term,
                predicate=self._namespace.active,
                default=True,
                as_string=True,
            ),
            alt_labels=alt_labels,
            abbreviation=self.get_value(
                subject=term, predicate=self._namespace.abbreviation, as_string=True
            ),
        )

    def extract_concept(self, concept: URIRef):
        """Extract a MeSH concept and its associated terms.

        Args:
            concept: IRI of the MeSH concept to extract.

        Returns:
            MeSHConcept: A populated MeSH concept model containing the
                preferred term and all terms linked to the concept.
        """
        preferred_term = self.get_value(
            subject=concept, predicate=self._namespace.preferredTerm
        )
        terms = [self.extract_term(term) for term in self._get_linked_terms(concept)]
        return MeSHConcept(
            iri=str(concept),
            id=self.get_value(
                subject=concept, predicate=self._namespace.identifier, as_string=True
            ),
            label=self._get_label(concept),
            is_active=self.get_value(
                subject=concept,
                predicate=self._namespace.active,
                default=True,
                as_string=True,
            ),
            scope_note=self.get_value(
                subject=concept, predicate=self._namespace.scopeNote, as_string=True
            ),
            preferred_term=self.extract_term(preferred_term),
            terms=terms if len(terms) > 0 else None,
        )

    def extract_concepts(self) -> Iterator[MeSHConcept]:
        """Yield all MeSH concepts found in the graph.

        Returns:
            Iterator[MeSHConcept]: Populated MeSH concept models.
        """
        for concept in self._graph.subjects(RDF.type, self._namespace.Concept):
            yield self.extract_concept(concept)
