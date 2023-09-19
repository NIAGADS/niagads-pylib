""" ontology parser
more details to be added
https://www.michelepasin.org/blog/2011/07/18/inspecting-an-ontology-with-rdflib/index.html

Author: fossilfriend

see https://owlready2.readthedocs.io for help w/owlready2

some additional info that is helpful to know:
owlready2 creates modules from the ontology structure, meanig

classes === python class and need to be instantiated before accessed
    - e.g., for c in ontoloy.classes():
                c().get_iri()
                c().get_properties()
"""
import argparse
import logging

from rdflib.namespace import OWL, RDF, RDFS
from rdflib import Graph, URIRef
from os import path
from owlready2 import get_ontology

from ..utils.sys import create_dir
from ..utils.logging import ExitOnExceptionHandler
from ..utils.string import xstr
from ..ontologies import ANNOTATION_PROPERTY_TYPES, OntologyTerm, ORDERED_PROPERTY_LABELS

LOGGER = logging.getLogger(__name__)

def get_term_properties(term: OntologyTerm, relIter):
    """exract annotation properties for the specified term

    Args:
        term (OntologyTerm): ontology term object
        relIter (generator): (relationship iterate), just predicates & objects

    Returns:
        update term
    """
    for predicate, object in relIter:
        property = path.basename(str(predicate))
        if '#' in property:
            property = property.split('#')[1]
        if term.valid_annotation_property(property):
            term.set_annotation_property(property, str(object))
        elif property == 'label':
            term.set_term(str(object))
        elif property == 'subClassOf':
            parentId = str(object)
            if parentId.startswith('N'): # BNode, not handling for now (nested or restricted axiom)
                continue
            else:
                parentId = path.basename(parentId)
                term.add_parent(parentId)
    return term
        

def main():
    parser = argparse.ArgumentParser(description="OWL (ontology RDF) file parser", allow_abbrev=False)
    parser.add_argument('--owlUrl', required=True,
                        help="URL for the OWL file (use purl.obolibrary.org URL when possible)")
    parser.add_argument('--outputDir', required=True,
                        help="full path to output directory")
    parser.add_argument('--debug', help="log debugging statements", action='store_true')
    parser.add_argument('--namespace', help="only retrieve terms from specified namespace (e.g., CLO)")
    parser.add_argument('--skipOntologies', 
                        help="comma separated list of referenced ontologies (ID prefixes/namespace) to skip when generating the term list (e.g., UBERON, DOID)")
    args = parser.parse_args()
    
    outputPath = create_dir(args.outputDir)
    logging.basicConfig(
            handlers=[ExitOnExceptionHandler(
                filename=path.join(outputPath, 'owl-parser.log'),
                mode='w',
                encoding='utf-8',
            )],
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.DEBUG if args.debug else logging.INFO)
    
    try:
        LOGGER.info("Loading ontology file from: " + args.owlUrl)
        graph = Graph()
        graph.parse(args.owlUrl, format="xml")
        
        LOGGER.info("Done parsing ontology")
        LOGGER.info("Size of ontology: " + xstr(len(graph)))

        subjects = graph.subjects()
        validTerms = []
        with open(path.join(outputPath, "terms.txt"), 'w') as tfh:
            print('\t'.join(ORDERED_PROPERTY_LABELS), file=tfh)
            for s in subjects:
                term = OntologyTerm(str(s))
                if (args.namespace and term.in_namespace(args.namespace)) or (not args.namespace):
                    term = get_term_properties(term, graph.predicate_objects(subject=s))
                    print(str(term), file=tfh)   
                    validTerms.append(term)

    except Exception as err:
        LOGGER.exception("Error parsing ontology")

    
