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
import json

from rdflib import Graph, URIRef
from os import path
from owlready2 import get_ontology, Ontology

from ..utils.sys import create_dir, generator_size
from ..utils.logging import ExitOnExceptionHandler
from ..utils.list import qw, flatten
from ..ontologies import OntologyTerm, ORDERED_PROPERTY_LABELS, parse_subclass_relationship, LABEL_URI, ANNOTATION_PROPERTIES

logger = logging.getLogger(__name__)
validAnnotationProps = flatten(list(ANNOTATION_PROPERTIES.values()))

def set_annotation_properties(term: OntologyTerm, relIter):
    """extract annotation properties from term relationships

    Args:
        term (OntologyTerm): ontology term to be annotated
        relIter (iterator): rdflib triples iterator (predicates & objects) of relationships

    Returns:
        updated term
    """
    for predicate, object in relIter:
        property = path.basename(str(predicate))
        if '#' in property:
            property = property.split('#')[1]
            
        if property == 'label':
            term.set_term(str(object))
        elif property in validAnnotationProps:
            term.set_annotation_property(property, str(object))

    return term


def set_relationships(term: OntologyTerm, ontology: Ontology):
    """_summary_

    Args:
        term (OntologyTerm): ontology term to be annotated
        ontology (Ontology): owlready2 ontology representation

    Raises:
        ValueError: if term not found in ontology

    Returns:
        updated term
    """
    try:
        owlClass = ontology.search(iri = "*" + term.get_id())
        if len(owlClass) == 0:
            raise ValueError("Term " + id + " not found in ontology.")
        relationships = [str(c) for c in owlClass[0].is_a]
        term.set_is_a(relationships)
        return term
    except ValueError as err:
        logger.exception(err)


def annotate_term(term: OntologyTerm, relIter, ontology: Ontology, labelOnly=False):
    """exract annotation properties & relationships for the specified term
    
    although rdflib can be used to get is_a relationships its a bit cumbersone
    so using owlready2, that's why we only extract the annotation properties 
    from the rdflib triples iterator

    Args:
        term (OntologyTerm): ontology term object
        relIter (generator): partial 'triples' iterator; if labelOnly objects iterator; if not labelOnly predicates & objects
        ontology (Ontology): owlready2 parsed ontology object
        labelOnly (boolean, optional): only fetch label
    Returns:
        update term
    """
    
    if labelOnly:
        term.set_term(str(next(relIter, term.get_id()))) # some terms may not have labels
    else:
        term = set_annotation_properties(term, relIter)
        term = set_relationships(term, ontology)
    return term
        
        
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
    write synonyms to file

    Args:
        term (OntologyTerm): ontology term
        file (obj): file handler
    """
    synonyms = term.get_synonyms()
    if synonyms is not None:
        id = term.get_id()
        for s in synonyms:
            print(id, s, sep='\t', file=file)


def write_relationships(term: OntologyTerm, file):
    """write relationships to file

    Args:
        term (OntologyTerm): ontology term
        file (obj): file handler
    """
    subjectTermId = term.get_id()
    relationships = term.is_a()
    for r in relationships:
        parsedR = parse_subclass_relationship(r)
        objectTermId = parsedR if isinstance(parsedR, str) else 'NULL'
        relJson = 'NULL' if isinstance(parsedR, str) else json.dumps(parsedR) 
        relStr = 'NULL' if isinstance(parsedR, str) else r
        print(subjectTermId, objectTermId, relStr, relJson, sep="\t", file=file)   
            
            
def create_files(dir: str):
    """create file handles / output header

    Args:
        dir (str): output directory

    Returns:
        term, relationship, and synoynm file handlers
    """
    tfh = open(path.join(dir, "terms.txt"), 'w')
    print('\t'.join(ORDERED_PROPERTY_LABELS), file=tfh, flush=True)  
        
    rfh = open(path.join(dir, "relationships.txt"), 'w')
    print('\t'.join(qw('subject_term_id object_term_id triple triple_json', returnTuple=True)), file=rfh, flush=True)

    sfh = open(path.join(dir, "synonyms.txt"), 'w')
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
            logger.warn("namespace '" + args.namespace + "' specified; term file may not contain all terms in relationships")
        
        if args.verbose:
            logger.info("Loading ontology graph file from: " + args.url)
        
        # using rdflib for extracting annotation properties
        graph = Graph()
        graph.parse(args.url, format="xml") 
        
        # using owlready2 for following axioms/is_a relationships
        # extra overhead but logistically easier
        ontology = get_ontology(args.url) 
        ontology.load()
        
        if args.verbose:
            logger.info("Done loading ontology")
            logger.info("Found " + str(len(graph)) + " ontology terms (incl. blind nodes)")

        if args.verbose:
            logger.info("Extracting terms and annotations")
            
        termFh, relFh, synFh = create_files(outputPath)
        
        subjects = graph.subjects()                 
        count = 0
        termCount = 0
        for s in subjects:
            count += 1
            if isinstance(s, URIRef): # ignore rdflib Blind Nodes     
                term = OntologyTerm(str(s))
                
                inNamespace = (args.namespace and term.in_namespace(args.namespace)) or (not args.namespace)  
                labelOnly = not inNamespace
                
                relationIterator = graph.objects(subject=s, predicate=URIRef(LABEL_URI)) \
                    if labelOnly else graph.predicate_objects(subject=s)
                    
                term = annotate_term(term, relationIterator, ontology, labelOnly=labelOnly)
                
                write_term(term, termFh)
                
                if inNamespace:
                    write_synonyms(term, synFh)
                    write_relationships(term, relFh)
                                    
                termCount += 1
                if termCount % 5000 == 0 and args.verbose:
                    logger.info("Parsed " + str(count) + " ontology terms; found " + str(termCount) + " valid terms")
        
        if args.verbose:
            logger.info("DONE. Parsed " + str(count) + " ontology terms; found " + str(termCount) + " valid terms")
            
        termFh.close()
        relFh.close()
        synFh.close()

    except Exception as err:
        logger.exception("Error parsing ontology")

    
