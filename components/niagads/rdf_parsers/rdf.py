"""RDF parsing utilities for handling RDF/N-Triples data.

This module provides classes for parsing and querying RDF graphs, with
support for various RDF serialization formats. Utilizes rdflib for efficient
graph operations.
"""

from typing import Iterator

from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.helpers import get_field_iri
from niagads.common.reference.ontologies.models import OntologyTerm
from rdflib import Graph, Namespace, URIRef


class RDFParser(ComponentBaseMixin):
    """Base parser for RDF graphs.

    Provides common functionality for parsing and querying RDF data
    from various serialization formats using rdflib.
    """

    def __init__(
        self,
        file: str,
        namespace=None,
        format=None,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """Initialize the RDFParser.

        Args:
            file: Path to the RDF file to parse.
            namespace: Optional namespace URI for the RDF graph.
            format: RDF serialization format (e.g., 'xml', 'nt', 'ttl').
                If None, rdflib will attempt to auto-detect the format.
            logger: Optional logger instance for debug/info messages.
            debug: If True, enable debug mode for verbose output.
            verbose: If True, enable verbose logging output.
        """
        super().__init__(logger=logger, debug=debug, verbose=verbose)
        self._namespace = Namespace(namespace)
        self._graph = Graph()
        self.logger.debug("Parsing RDF Graph")
        self._graph.parse(file, format=format)  # should auto detect format if None
        self.logger.debug(
            f"Done parsing RDF Graph.  Found {len(set(self._graph.subjects()))}"
            f" subjects and {len(set(self._graph.predicates()))} relationships"
        )

    def get_value(
        self,
        subject: URIRef = None,
        predicate: URIRef = None,
        object: URIRef = None,
        default=None,
        as_string: bool = False,
    ):
        """Retrieve a value from the RDF graph using a triple pattern.

        Query the RDF graph with the provided subject, predicate, and/or
        object to retrieve a matching value.

        Args:
            subject: Optional subject URIRef to match.
            predicate: Optional predicate URIRef to match.
            object: Optional object URIRef to match.
            default: Default value to return if no match is found.
            as_string: If True, convert the result to a string before returning.

        Returns:
            The matched value from the RDF graph, converted to string if
            as_string is True, or the default value if no match is found.

        Raises:
            rdflib.term.UniquenessError: If multiple matching triples are found
                in the graph.
        """
        value = self._graph.value(
            subject, predicate, object, default=default, any=False
        )
        return str(value) if as_string and value is not None else value


class NTriplesParser(RDFParser):
    """Parser for RDF N-Triples format.

    A specialized parser that handles RDF data in N-Triples format
    (plaintext, line-based RDF representation).
    """

    def __init__(
        self,
        file: str,
        namespace=None,
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """Initialize the NTriplesParser.

        Args:
            file: Path to the N-Triples (.nt) file to parse.
            namespace: Optional namespace URI for the RDF graph.
            logger: Optional logger instance for debug/info messages.
            debug: If True, enable debug mode for verbose output.
            verbose: If True, enable verbose logging output.
        """
        super().__init__(
            file=file,
            format="nt",
            namespace=namespace,
            logger=logger,
            debug=debug,
            verbose=verbose,
        )
