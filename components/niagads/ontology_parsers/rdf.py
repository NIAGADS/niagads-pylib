from typing import Iterator

from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.helpers import get_field_iri
from niagads.common.reference.ontologies.models import OntologyTerm

from rdflib import BNode, Graph, Literal, URIRef


class RDFParser(ComponentBaseMixin):
    def __init__(
        self, file: str, logger=None, debug: bool = False, verbose: bool = False
    ):
        super().__init__(logger=logger, debug=debug, verbose=verbose)
        self._graph = Graph()
        if self._verbose:
            self.logger.info("Parsing RDF File")
        self._graph.parse(file)  # auto detect format


class NTriplesParser(RDFParser):
    def __init__(
        self, file: str, logger=None, debug: bool = False, verbose: bool = False
    ):
        super().__init__(logger=logger, debug=debug, verbose=verbose)
        self._graph = Graph()
        if self._verbose:
            self.logger.info("Parsing N-Triples")
        self._graph.parse(file, format="nt")


class MeSHTriplesParser(NTriplesParser):
    def extract_descriptors(self) -> Iterator[dict]:
        """q"""
        pass

    def extract_concepts(self) -> Iterator[dict]:
        pass
