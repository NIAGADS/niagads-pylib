import csv
from enum import auto

from niagads.csv_parser.core import CSVFileParser
from niagads.enums.core import CaseInsensitiveEnum
from rdflib import Graph, Literal, Namespace, URIRef


class RDFTripleType(CaseInsensitiveEnum):
    CLASS_HIERARCHY = auto()
    SEMANTIC = auto()


class CSVTriplesParser:
    def __init__(
        self,
        fileName: str,
        parserType: RDFTripleType = RDFTripleType.SEMANTIC,
        namespace: str = "http://example.com/ns#",
    ):
        self.__csvFile = fileName
        self.__namespace = namespace
        self.__parserType = parserType
        self.__graph = Graph()
        self.__graph.bind("ex", self.__namespace)

    # TODO - set relationship type for class hierarchy

    def parse(self):
        delimiter = CSVFileParser(self.__csvFile).sniff()
        with open(self._csvFile, "r") as fh:
            reader = csv.reader(fh, delimiter=delimiter)
            for row in reader:
                pass


"""import csv


# Create an RDF graph
g = Graph()

# Define namespaces (optional, but good practice)
ns = Namespace("http://example.com/ns#")
g.bind("ex", ns)

# Open the CSV file
with open('data.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)

    # Iterate through each row
    for row in reader:
        # Create a resource (subject) based on a unique identifier (e.g., ID column)
        subject = URIRef(ns + row['ID'])

        # Create triples for each column (predicate and object)
        g.add((subject, ns['name'], Literal(row['Name'])))
        g.add((subject, ns['age'], Literal(row['Age'])))

# Serialize the graph to a Turtle file (or other RDF format)
g.serialize(destination="data.ttl", format="turtle")"""
