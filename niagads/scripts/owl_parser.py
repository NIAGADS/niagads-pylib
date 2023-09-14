""" ontology parser
more details to be added

Author: fossilfriend
"""
import argparse
import logging
from os import path
from owlready2 import get_ontology
from ..utils.sys import warning, create_dir, ExitOnExceptionHandler

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
        logger.info("Fetching ontology file from: " + args.owlUrl)
        ontology = get_ontology(args.owlUrl)
        logger.info("Parsing ontology")
        ontology.load()
    except Exception as err:
        logger.exception("Error fetching ontology")

    

# nto_path.append("/path/to/your/local/ontology/repository")
#>>> onto = get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/pizza_onto.owl")
#>>> onto.load()