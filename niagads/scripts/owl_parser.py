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

from rdflib import Graph
from os import path
from owlready2 import get_ontology, Ontology, Thing

from ..utils.sys import create_dir
from ..utils.logging import ExitOnExceptionHandler
from ..utils.string import xstr, regex_replace
from ..ontologies import OntologyTerm, ORDERED_PROPERTY_LABELS

LOGGER = logging.getLogger(__name__)

def set_annotation_properties(term: OntologyTerm, relIter):
    for predicate, object in relIter:
        property = path.basename(str(predicate))
        if '#' in property:
            property = property.split('#')[1]
        if term.valid_annotation_property(property):
            term.set_annotation_property(property, str(object))
        elif property == 'label':
            term.set_term(str(object))
            
    return term


def set_relationships(term: OntologyTerm, ontology: Ontology):
    owlClass = ontology.search(iri = "*" + term.get_id())[0]
    relationships = [regex_replace('^[a-z]+.', '', str(c)) for c in owlClass.is_a]
    term.set_is_a(relationships)
    return term


def annotate_term(term: OntologyTerm, relIter, ontology: Ontology):
    """exract annotation properties & relationships for the specified term
    
    although rdflib can be used to get is_a relationships its a bit cumbersone
    so using owlready2, that's why we only extract the annotation properties 
    from the rdflib triples iterator

    Args:
        term (OntologyTerm): ontology term object
        relIter (generator): partial 'triples' iterator, just predicates & objects for the subject defined by the term
        ontology (Ontology): owlready2 parsed ontology object
    Returns:
        update term
    """
   
    term = set_annotation_properties(term, relIter)
    term = set_relationships(term, ontology)
    return term
        
        
def get_terms(graph: Graph, ontology: Ontology):
    subjects = graph.subjects()
    terms = {}
    for s in subjects:
        term = OntologyTerm(str(s))
        term = annotate_term(term, graph.predicate_objects(subject=s), ontology)
        terms = {term.get_id() : term}     
         
    return terms

def write_terms(terms, outputPath: str, namespace=None):
    with open(path.join(outputPath, "terms.txt"), 'w') as fh:
        print('\t'.join(ORDERED_PROPERTY_LABELS), file=fh)       
        for t in terms.values():
            if (namespace and t.in_namespace(namespace)) or (not namespace):
                    print(str(t), file=fh)   

def main():
    parser = argparse.ArgumentParser(description="OWL (ontology RDF) file parser", allow_abbrev=False)
    parser.add_argument('--debug', help="log debugging statements", action='store_true')
    parser.add_argument('--verbose', help="run in verbose mode (will log INFO statements)", action='store_true')
    parser.add_argument('--url', required=True,
                        help="URL for the OWL file (use purl.obolibrary.org URL when possible)")
    parser.add_argument('--outputDir', required=True,
                        help="full path to output directory")
    parser.add_argument('--namespace', help="only retrieve terms from specified namespace (e.g., CLO)")
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
        if args.namespace:
            LOGGER.warn("--namespace '" + args.namespace + "' specified; term file may not contain all terms in relationships")
        
        if args.verbose:
            LOGGER.info("Loading ontology graph file from: " + args.url)
        
        # using rdflib for extracting annotation properties
        graph = Graph()
        graph.parse(args.url, format="xml") 
        
        # using owlready2 for following axioms/is_a relationships
        # extra overhead but logistically easier
        ontology = get_ontology(args.url) 
        ontology.load()
        
        if args.verbose:
            LOGGER.info("Done parsing ontology")
            LOGGER.info("Size of ontology: " + xstr(len(graph)))


        terms = get_terms(graph, ontology)
        write_terms(terms, outputPath, args.namespace)
        
            
                

    except Exception as err:
        LOGGER.exception("Error parsing ontology")

    
