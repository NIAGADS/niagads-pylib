""" ontology parser
Parses an OWL file representing an ontology and generates 3 tab-delimited file:

terms.txt - contains basic term identification
------------------------------------------------
term_id, term, iri, db_refs, definition, comments, and obsolete/deprecated flags

synonyms.txt - contains term_id - synonym (raw term, not ID) pairs
------------------------------------------------

relationships.txt - term 'is_a'/'subclass_of' relationships
------------------------------------------------
contains either subject_id / object_id pairs or 
subject_id / parsed triple string (for relationships with restrictions or logic)

in all files, missing or irrelevant information are indicated by 'NULL'

Author: fossilfriend

see https://owlready2.readthedocs.io for help w/owlready2
see https://rdflib.readthedocs.io/en/stable/ for help w/rdflib
"""
import argparse
import logging
import json

from os import path
from sys import stdout

from functools import partial
from rdflib import Graph, URIRef
from owlready2 import get_ontology, Ontology
from multiprocessing import Pool, cpu_count, SimpleQueue

from ..utils.sys import create_dir, generator_size, remove_duplicate_lines
from ..utils.logging import ExitOnExceptionHandler
from ..utils.list import qw, flatten
from ..ontologies import OntologyTerm, ORDERED_PROPERTY_LABELS, parse_subclass_relationship, ANNOTATION_PROPERTIES, IMPORTED_FROM

logger = logging.getLogger(__name__)
validAnnotationProps = flatten(list(ANNOTATION_PROPERTIES.values()))

def init_worker(graph: Graph, ontology: Ontology, debug: bool):
    """initialize parallel worker with large data structures 
    or 'global' information'
    so they can be shared amongs the processors
    see https://superfastpython.com/multiprocessing-pool-shared-global-variables/

    Args:
        graph (Graph): ontology in rdflib Graph format (for accessing annotation properties)
        ontology (Ontology): ontology in owlready2 Ontology format (for accessing parsed nested is_a relationships)
    """
    # declare scope of new global variable
    global sharedGraph
    global sharedOntology
    global sharedDebugFlag

    sharedGraph = graph
    sharedOntology = ontology
    sharedDebugFlag = debug

    
def set_annotation_properties(term: OntologyTerm, relIter):
    """extract annotation properties from term relationships

    Args:
        term (OntologyTerm): ontology term to be annotated
        relIter (iterator): rdflib triples iterator (predicates & objects) of relationships

    Returns:
        updated term
    """ 
    global sharedDebugFlag
    
    for predicate, object in relIter:
        property = path.basename(str(predicate))
        if property == IMPORTED_FROM:
            return None
        if '#' in property:
            property = property.split('#')[1]
            
        if property == 'label':
            term.set_term(str(object))
        elif property in validAnnotationProps:
            term.set_annotation_property(property, str(object))
            
    if sharedDebugFlag:
        logger.debug(term.get_id() + " - END - properties")
 
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
    global sharedDebugFlag
    
    try:
        owlClass = ontology.search(iri = "*" + term.get_id())
        if len(owlClass) == 0:
            return term
        relationships = [str(c) for c in owlClass[0].is_a]
        term.set_is_a(relationships)
        if sharedDebugFlag:
            logger.debug(term.get_id() + " - DONE - relationships")
        return term
    except ValueError as err:
        logger.exception(err)


def parallel_annotate_term(subject: URIRef):
    """ worker function called by the multiproccessing pool to extract
    annotation properties and relationshisp for the specific term
    
    relies on the following pool shared resources:
    
    sharedGraph: rdflib graph representation of the ontology,
        for accessing annotation properties
        
    sharedOntology: owlready2 ontology representation of the ontology; 
        for accessing parsed is_a relationships
        

    NOTE: although rdflib can be used to get is_a relationships, its a bit cumbersone
    so using owlready2 which returns them in a nice string format, 
    that's why we only extract the annotation properties 
    from the rdflib triples iterator

    Args:
        subject (URIRef): term to be annotated, identified by its IRI

    Returns:
        term (OntologyTerm): annotated term
    """
    # declare scope of shared variables
    global sharedGraph
    global sharedOntology
    global sharedDebugFlag
    
    term = OntologyTerm(str(subject))  
    if sharedDebugFlag:
        logger.debug(term.get_id() + " - START")
        
    relationIterator = sharedGraph.predicate_objects(subject=subject) 
    
    if sharedDebugFlag:
        logger.debug(term.get_id() + " - START - properties")
        
    term = set_annotation_properties(term, relationIterator)
    if term is None: # will happen if properties reveal the term is imported and so not fully annotated in the OWL file
        return None
    
    if sharedDebugFlag:
        logger.debug(term.get_id() + " - START - relationships")
    term = set_relationships(term, sharedOntology)
    
    if sharedDebugFlag:
        logger.debug(term.get_id() + " - END - annotated")
    return term


def write_term(term: OntologyTerm, file):
    """
     write term to terms.txt file

    Args:
        term (OntologyTerm): the ontology term
        file (obj): file handler
    """
    print(str(term), file=file)   


def write_dbrefs(term: OntologyTerm, file):
    """
    write DB Refs to file

    Args:
        term (OntologyTerm): ontology term
        file (obj): file handler
    """
    refs = term.get_db_refs()
    if refs is not None:
        id = term.get_id()
        for r in refs:
            print(id, r, sep='\t', file=file)   


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
    fields = ORDERED_PROPERTY_LABELS
    fields.remove("comment")
    print('\t'.join(fields), file=tfh, flush=True)  
        
    rfh = open(path.join(dir, "relationships.txt"), 'w')
    print('\t'.join(qw('subject_term_id object_term_id triple triple_json', returnTuple=True)), file=rfh, flush=True)

    sfh = open(path.join(dir, "synonyms.txt"), 'w')
    print('\t'.join(qw('subject_term_id synonym', returnTuple=True)), file=sfh, flush=True)
    
    dfh = open(path.join(dir, "dbrefs.txt"), 'w')
    print('\t'.join(qw('subject_term_id db_ref', returnTuple=False)), file=dfh, flush=True)
    
    return tfh, rfh, sfh, dfh


def clean_subjects(graph: Graph):
    # remove blind nodes and transform iterator to list so can use multiprocessing.imap   
    # remove duplicates
    subjects = graph.subjects()
    reference = {}
    cleanSubjects = []
    for s in subjects:
        id = str(s)
        if id not in reference and isinstance(s, URIRef):
            reference[id] = True
            cleanSubjects.append(s)
    return cleanSubjects


def main():
    parser = argparse.ArgumentParser(description="OWL (ontology RDF) file parser", allow_abbrev=False,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--debug', help="log debugging statements", action='store_true')
    parser.add_argument('--verbose', help="run in verbose mode (will log INFO statements)", action='store_true')
    parser.add_argument('--url', required=True,
                        help="URL for the OWL file (use purl.obolibrary.org URL when possible)")
    parser.add_argument('--outputDir', required=True,
                        help="full path to output directory")
    parser.add_argument('--namespace', help="only write terms from specified namespace (e.g., CLO)")
    parser.add_argument('--numWorkers', help="number of workers for parallel processing, default = #CPUs", type=int, default=cpu_count())
    parser.add_argument('--reportSuccess', action='store_true', help="for third party calls, report SUCCESS when complete")
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
            logger.info("Pruning blind nodes")
        
        # remove blind nodes and duplicates
        subjects = clean_subjects(graph)
        # subjects = [s for s in graph.subjects() if isinstance(s, URIRef)]
        
        if args.verbose:
            logger.info("Found " + str(len(subjects)) + " ontology terms")
            logger.info("Extracting terms and annotations in parallel")
                    
        termFh, relFh, synFh, refFh = create_files(outputPath)
        
        # see https://superfastpython.com/multiprocessing-pool-shared-global-variables/
        # for more info on shared 'globals' passed through custom initializer & initargs
        with Pool(args.numWorkers, initializer=init_worker, initargs=(graph, ontology, args.debug)) as pool:
            if args.debug:
                logger.debug("Starting parallel processing of subjects; max number workers = " + str(args.numWorkers))
                
            terms = pool.imap(parallel_annotate_term, [s for s in subjects])
        
            if args.verbose:
                logger.info("Parsing ontology terms and writing files.")
                
            count = 0
            importCount = 0
            for term in terms:
                if term is None: # imported
                    importCount = importCount + 1
                    continue
                
                if args.debug:
                    logger.debug(term.get_id() + " - WRITING - term")
                    
                write_term(term, termFh)
                
                # terms get fully annotated b/c obsolete flags can be in relationships
                # filter for namespace after annotation is complete
                termOnly = False if args.namespace is None \
                    else not (args.namespace and term.in_namespace(args.namespace))
                    
                if not termOnly:
                    if args.debug:
                        logger.debug(term.get_id() + " - WRITING - relationships")
                        
                    write_relationships(term, relFh)    

                    if args.debug:
                        logger.debug(term.get_id() + " - WRITING - synonyms")    
                                
                    write_synonyms(term, synFh)
                    
                    if args.debug:
                        logger.debug(term.get_id() + " - WRITING - dbrefs")
                        
                    write_dbrefs(term, refFh)
                    
                if args.debug:
                    logger.debug(term.get_id() + " - WRITING - END")
                    
                count = count + 1
                if args.verbose and count % 5000 == 0:
                    logger.info("Output " + str(count) + " ontology terms")
        
            logger.info("Done.  Parsed " + str(count) + " ontology terms")
            logger.info("Skipped " + str(importCount) + " imported ontology terms")
            logger.info("Removing duplicates from 'terms.txt file")
            termFh.close()
            remove_duplicate_lines(path.join(outputPath, "terms.txt"), header=True, overwrite=True)
        
        if args.reportSuccess:
            print("SUCCESS", file=stdout)
    except Exception as err:
        logger.exception("Error parsing ontology")
        # report success
        if args.reportSuccess:
            print("FAIL", file=stdout)
            
    finally:
        # close the file handlers, if they exist                                    
        if 'termFh' in locals(): termFh.close()
        if 'relFh' in locals(): relFh.close()
        if 'synFh' in locals(): synFh.close()
        if 'refFh' in locals(): refFh.close()
        
    
