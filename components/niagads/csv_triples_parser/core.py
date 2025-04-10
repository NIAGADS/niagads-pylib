import csv
from enum import auto
from typing import List

from niagads.csv_parser.core import CSVFileParser
from niagads.enums.core import CaseInsensitiveEnum
from niagads.string_utils.core import generate_uuid
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef, OWL


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

        self.__namespace: Namespace = Namespace(f"https://www.niagads.org/{ontology}#")
        self.__graph: Graph = Graph()
        self.__graph.bind(ontology, self.__namespace)
        self.__graph.bind("owl", OWL)  # use OWL namespace

        # TODO - set relationship type for class hierarchy? or assume `is_a`?

    def get_defintions(self):
        return self.__definitions

    def parse_semantic_triple(self, values: List[str]):
        raise NotImplementedError("Semantic triple parsing not yet implemented.")

    def add_owl_class(self, value: str):
        node = URIRef(self.__namespace[generate_uuid(value)])

        self.__graph.add((node, RDF.type, OWL.Class))
        self.__graph.add((node, RDFS.subClassOf, OWL.Thing))
        self.__graph.add((node, RDFS.label, Literal[value]))

        return node

    def parse_class_hierarchy_triple(self, values: List[str]):
        """class subclass term
        subclass is_a class, term is_a subclass
        """

        classNode = self.add_owl_class(values[0])
        subClassNode = self.add_owl_class(values[1])
        termNode = self.add_owl_class(values[2])

        self.__graph.add(subClassNode, RDFS.subClassOf, classNode)
        self.__graph.add(termNode, RDFS.subClassOf, subClassNode)

    def parse(self):
        delimiter = CSVFileParser(self.__csvFile).sniff()
        with open(self.__csvFile, "r") as fh:
            reader = csv.reader(fh, delimiter=delimiter)
            for row in reader:
                if self.__parserType == RDFTripleType.SEMANTIC:
                    self.parse_semantic_triple(row)
                else:
                    self.parse_class_hierarchy_triple(row)


# Serialize the graph to a Turtle file (or other RDF format)
# g.serialize(destination="data.ttl", format="turtle")"""
