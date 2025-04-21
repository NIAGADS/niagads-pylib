import csv
from enum import auto
from typing import List

from niagads.csv_parser.core import CSVFileParser
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.string import blake2b_hash
from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, Namespace, URIRef


class RDFTripleType(CaseInsensitiveEnum):
    CLASS_HIERARCHY = auto()
    SEMANTIC = auto()


class CSVTriplesParser:
    def __init__(
        self,
        file: str,
        definitionFile: str = None,
        parserType: RDFTripleType = RDFTripleType.SEMANTIC,
        ontology: str = "niagads",
    ):
        self.__csvFile = file
        self.__definitions = (
            CSVFileParser(definitionFile).to_json()
            if definitionFile is not None
            else None
        )
        self.__parserType: RDFTripleType = RDFTripleType(parserType)

        self.__namespace: Namespace = Namespace(
            f"http://ontology.niagads.org/{ontology}#"
        )
        self.__graph: Graph = Graph()
        self.__graph.bind(ontology, self.__namespace)
        self.__graph.bind("owl", OWL)  # use OWL namespace
        self.__graph.bind("skos", SKOS)  # use OWL namespace

        # TODO - set relationship type for class hierarchy? or assume `is_a`?

    def get_defintions(self):
        """Return the definition map"""
        return self.__definitions

    def parse_semantic_triple(self, triple: List[str]):
        """Parse a subject <-> predicate <-> object triple"""
        raise NotImplementedError("Semantic triple parsing not yet implemented.")

    def add_owl_class(self, label: str):
        """
        create and add a new class node
            node is of type OWL.Class
            node is subClassOf OWL.Thing
            node label = value
            node definition = self.__defintions[label]

        Args:
            label (str): the label of the node

        Returns:
            URIRef : the URIRef for the node
        """
        # generate a unique URI by hashing the label
        node = URIRef(self.__namespace[blake2b_hash(label, 4)])

        # add the node and categorization as OWL.Class/OWL.Thing to the graph
        self.__graph.add((node, RDF.type, OWL.Class))
        self.__graph.add((node, RDFS.subClassOf, OWL.Thing))
        self.__graph.add((node, RDFS.label, Literal(label)))

        # check to see if a definition exists, if so add that relationship
        if label in self.__definitions:
            self.__graph.add(
                (node, SKOS.definition, Literal(self.__definitions[label]))
            )

        return node

    def parse_class_hierarchy_triple(self, triple: List[str]):
        """
        assumes a list of values contains a triple of: class <-> subclass <-> term

        creates a node each for class, subclass, and term
        creates the following relationships
            subclass is a subClassOf class
            term is a subClassOf subclass

        Args:
            values (List[str]): list containing the class <-> subclass <-> term triple
        """

        classNode = self.add_owl_class(triple[0].strip())
        subClassNode = self.add_owl_class(triple[1].strip())
        termNode = self.add_owl_class(triple[2].strip())

        self.__graph.add((subClassNode, RDFS.subClassOf, classNode))
        self.__graph.add((termNode, RDFS.subClassOf, subClassNode))

    def parse(self, header: bool = False):
        """
        parse the triples file

        Args:
            header (bool, optional): set to `True` if file contains header row to be ignored. Defaults to False.
        """
        delimiter = CSVFileParser(self.__csvFile).sniff()
        with open(self.__csvFile, "r") as fh:
            reader = csv.reader(fh, delimiter=delimiter)
            if header:
                next(reader, None)  # skip the header

            for row in reader:
                if self.__parserType == RDFTripleType.SEMANTIC:
                    self.parse_semantic_triple(row)
                else:
                    self.parse_class_hierarchy_triple(row)

    def to_ttl(self, file: str = None):
        """Convert to turtle format
        see <https://www.w3.org/TR/turtle/> for specification

        if `file` is provided, will write the turtle formatted graph to file
        otherwise returns the turtle object

        Args:
            file (str, optional): write output to specified file. Defaults to None.

        Returns:
            str: formatted turtle (ttl) string
        """
        ttl = self.__graph.serialize(destination=file, format="ttl")
        if file is None:
            return ttl

    def to_owl(self, file: str = None, pretty: bool = False):
        """Convert to owl format; wrapper for `to_xml`, just ensures .owl extension on file name"""
        return self.to_xml(
            file.replace(".xml", ".owl") if file is not None else None, pretty
        )

    def to_xml(self, file: str = None, pretty: bool = False):
        """
        Convert to xml format

        Args:
            file (str, optional):  write output to specified file. Defaults to None.
            pretty (bool, optional): pretty print the xml. Defaults to False.

        Returns:
            str: formatted xml string
        """
        format = "pretty-xml" if pretty else "xml"
        xml = self.__graph.serialize(destination=file, format=format)
        if file is None:
            return xml
