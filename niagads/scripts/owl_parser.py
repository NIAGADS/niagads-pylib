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
import inspect

from rdflib.namespace import OWL, RDF, RDFS
from rdflib import Graph, URIRef


from os import path
from owlready2 import get_ontology, sync_reasoner
from ..utils.sys import warning, create_dir, get_class_properties, generator_size
from ..utils.logging import ExitOnExceptionHandler
from ..utils.string import xstr


def main():
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="OWL (ontology RDF) file parser", allow_abbrev=False)
    parser.add_argument('--owlUrl', required=True,
                        help="URL for the OWL file (use purl.obolibrary.org URL when possible)")
    parser.add_argument('--outputDir', required=True,
                        help="full path to output directory")
    parser.add_argument('--debug', help="log debugging statements", action='store_true')
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
        graph = Graph()
        logger.info("Loading ontology file from: " + args.owlUrl)
        graph.parse(args.owlUrl, format="xml")
        logger.info("Done parsing ontology")
        
        logger.info("Size of ontology: " + xstr(len(graph)))

        # get all nodes
        subjects = graph.subjects()
        for s in subjects:
            logger.info("--- " + str(s) + " ---")
            for p, o in graph.predicate_objects(subject=s):
                logger.info(str(p) + " -> " + str(o))
            logger.info("")
            # logger.info(s)
            # list all triples for the node n
            # logger.info(list(graph[s]))
            
            # check that http://www.w3.org/1999/02/22-rdf-syntax-ns#type -> http://www.w3.org/2002/07/owl#Class
            
            
  
        for s, p, o in graph: 
            if 'label' in p: 
              logger.info(str(s) + " -> " + str(p) + " -> " + str(o))
        
        # x = graph.subjects()
        # print(generator_size(graph.subjects()))
        # for subject in graph.subjects():
        #     for predicate in subject:
        #         print(predicate)
            
        # ontology = get_ontology(args.owlUrl)
        # ontology.load()
        
        # classes = ontology.classes()
        # for c in classes:
        #     # if c.name == 'CLO_0009464':
        #     logger.info(" ")
        #     logger.info(" /// " + c.name)
        #     if c.name == 'Thing':
        #         continue
        #     else:
        #         c()
        #     instances = c.instances()
            
        #     for instance in instances:
        #         logger.info("     --- start " + instance.name)
        #         for p in instance.get_properties():
        #             for value in p[instance]:
        #                 logger.info(".%s == %s" % (p.python_name, value))
        #         logger.info("     --- end " + instance.name)       
                

            
    except Exception as err:
        logger.exception("Error parsing ontology")

    
