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
                
TODO: simplify namespace filter
"""
import argparse
import logging

from typing import Dict
from rdflib import Graph, URIRef
from os import path
from owlready2 import get_ontology, Ontology, Thing

from ..utils.sys import create_dir
from ..utils.logging import ExitOnExceptionHandler
from ..utils.string import xstr, regex_replace
from ..utils.list import qw
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
    try:
        owlClass = ontology.search(iri = "*" + term.get_id())
        if len(owlClass) == 0:
            raise ValueError("Term " + term.get_id() + " not found in ontology.")
        relationships = [str(c) for c in owlClass[0].is_a]
        term.set_is_a(relationships)
        return term
    except Exception as err:
        LOGGER.exception(err)


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
        
        
def get_terms(graph: Graph, ontology: Ontology, namespace=None):
    """
    parse graph and ontology objects to extract terms, 
    their annotation properties, and is_a relationships

    Args:
        graph (Graph): rdflib graph object capturing ontology classes in nodes
        ontology (Ontology): owlready2 ontolog representation
        namespace (str, optional): only export terms in the specified namespace. Defaults to None.
        
    Returns:
        dict of { term_id: OntologyTerm } pairs
    """



def write_term(term: OntologyTerm, file):
    """
     write term to terms.txt file

    Args:
        term (OntologyTerm): the ontology term
        file (obj): file handler
    """
    print(str(term), file=file)   
                    

def write_synonyms(term: OntologyTerm, file):
    """
    _summary_

    Args:
        terms (OntologyTerm): {term_id: OntologyTerm} pairs
        file (obj): file handler
    """
    synonyms = term.get_synonyms()
    if synonyms is not None:
        id = term.get_id()
        for s in synonyms:
            print(id, s, sep='\t', file=file)
              

def write_relationships(term: OntologyTerm, file):
    relationships = term.is_a()
    if relationships is not None:
        for rel in relationships:
            LOGGER.info(rel)
                    
            
def create_files(outputPath):
    tfh = open(path.join(outputPath, "terms.txt"), 'w')
    print('\t'.join(ORDERED_PROPERTY_LABELS), file=tfh, flush=True)  
        
    rfh = open(path.join(outputPath, "relationships.txt"), 'w')
    print('\t'.join(qw('subject_term_id subject_term predicate_term_id predicate_term object_term_id object_term triple', returnTuple=True)), file=rfh, flush=True)

    sfh = open(path.join(outputPath, "synonyms.txt"), 'w')
    print('\t'.join(qw('subject_term_id synonym', returnTuple=True)), file=sfh, flush=True)
    
    return tfh, rfh, sfh
   

def main():
    parser = argparse.ArgumentParser(description="OWL (ontology RDF) file parser", allow_abbrev=False)
    parser.add_argument('--debug', help="log debugging statements", action='store_true')
    parser.add_argument('--verbose', help="run in verbose mode (will log INFO statements)", action='store_true')
    parser.add_argument('--url', required=True,
                        help="URL for the OWL file (use purl.obolibrary.org URL when possible)")
    parser.add_argument('--outputDir', required=True,
                        help="full path to output directory")
    parser.add_argument('--namespace', help="only write terms from specified namespace (e.g., CLO)")
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
            LOGGER.info("Done loading ontology")
            LOGGER.info("Size of ontology: " + xstr(len(graph)))

        if args.verbose:
            LOGGER.info("Extracting terms and annotations")
            
        termFh, relFh, synFh = create_files(outputPath)
        subjects = graph.subjects()
        for s in subjects:
            if isinstance(s, URIRef): # ignore rdflib Blind Nodes     
                term = OntologyTerm(str(s))
                if (args.namespace and term.in_namespace(args.namespace)) or (not args.namespace):
                    term = annotate_term(term, graph.predicate_objects(subject=s), ontology)
                    write_term(term, termFh)
                    write_synonyms(term, synFh)
                    write_relationships(term, relFh)

        termFh.close()
        relFh.close()
        synFh.close()
        
            
                

    except Exception as err:
        LOGGER.exception("Error parsing ontology")

    
