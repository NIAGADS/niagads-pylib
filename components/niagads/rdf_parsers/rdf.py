from typing import Iterator

from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.helpers import get_field_iri
from niagads.common.reference.ontologies.models import OntologyTerm
from rdflib import Graph, Namespace


class RDFParser(ComponentBaseMixin):

    def __init__(
        self,
        file: str,
        namespace=None,
        format=None,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(logger=logger, debug=debug, verbose=verbose)
        self._namespace = Namespace(namespace)
        self._graph = Graph()
        self._graph.parse(file, format=format)  # should auto detect format if None


class NTriplesParser(RDFParser):
    def __init__(
        self,
        file: str,
        namespace=None,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(
            file=file,
            format="nt",
            namespace=namespace,
            logger=logger,
            debug=debug,
            verbose=verbose,
        )
