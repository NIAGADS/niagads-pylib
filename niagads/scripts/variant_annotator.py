""" looks up a list of variants provided in a file
    # returns as JSON or tab-delimited text
    # output is to STDOUT
    # author: fossilfriend
"""
import argparse
import logging
from sys import stdout

from ..utils.sys import warning, ExitOnExceptionHandler
from ..api_wrapper import VariantRecord

REQUEST_URI = "https://api.niagads.org"

def read_variants(file):
    """ read list of variants from file; removing 'chr' and
    substituting M for MT when appropriate
    removes header if found

    Args:
        file (string): file name
    Returns:
        tuple of variants,
        flag indicating if 'chr' was removed so it can be added back later
    """
    with open(file) as fh:
        variants = fh.read().splitlines() 
        if variants[0].lower() in ['id', 'variant', 'variant_id', 'ref_snp_id']:
            variants.pop(0)
    return variants


def main():
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Look up a list of variants and retrieve annotation", allow_abbrev=False)
    parser.add_argument('--file', required=True,
                        help="new line separated list of variants, can be refSnpID or chr:pos:ref:alt")
    parser.add_argument('--database', choices=['genomics', 'advp'], default='genomics')
    parser.add_argument('--format', default="json", choices=['table', 'json'], 
                        help="output file format; JSON format will include a lot more information than the table format")
    parser.add_argument('--pageSize', default=200, choices = [50, 200, 300, 400, 500], type=int)
    parser.add_argument('--allConseqs', action="store_true",
                        help="retrieve all conseuqences, not just most severe")
    parser.add_argument('--nullStr', help="string for null values in .tab format", 
                        choices=['N/A', 'NA', 'NULL', '.', ''], default='')
    parser.add_argument('--debug', help="log debugging statements", action='store_true')
    args = parser.parse_args()
    
    logging.basicConfig( handlers=[ExitOnExceptionHandler(
                filename=args.file + '-variant-annotator.log',
                mode='w',
                encoding='utf-8',
            )],
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.DEBUG if args.debug else logging.INFO)
    
    try:
        variants = VariantRecord('genomics', REQUEST_URI, read_variants(args.file))
        variants.set_null_str(args.nullStr)
        variants.set_page_size(args.pageSize)
        if args.allConseqs: variants.retrieve_full_annotation()

        logger.info("Looking up " + str(variants.get_query_size()) + " variants")
        
        variants.fetch()
        variants.write_response(file=stdout, format=args.format)
    except Exception as err:
        logger.error("Error annotating variants", err, stack_info=True, exc_info=True)
        raise err
    