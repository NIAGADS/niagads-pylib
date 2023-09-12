# looks up a list of variants provided in a file
# returns as JSON or tab-delimited text
# output is to STDOUT
# author: fossilfriend

import argparse
import json
from sys import stdout

from niagads.utils.sys_utils import warning
from niagads.api_wrapper.records.variant import VariantRecord

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
        if variants[0].lower() in ['id', 'variant']:
            variants.pop(0)
    return variants

def main():
    parser = argparse.ArgumentParser(description="Look up a list of variants and retrieve annotation", allow_abbrev=False)
    parser.add_argument('--file', required=True,
                        help="new line separated list of variants, can be refSnpID or chr:pos:ref:alt")
    parser.add_argument('--database', choices=['genomics', 'advp'], default='genomics')
    parser.add_argument('--format', default="json", choices=['table', 'json'], 
                        help="output file format; JSON format will include a lot more information than the table format")
    parser.add_argument('--pageSize', default=200, choices = [50, 200, 300, 400, 500], type=int)
    parser.add_argument('--full', help="retrieve full annotation; when not supplied will just return variant IDS and most severe consequence", action="store_true")
    parser.add_argument('--nullStr', help="string for null values in .tab format", 
                        choices=['N/A', 'NA', 'NULL', '.', ''], default='')
    args = parser.parse_args()
    
    variants = VariantRecord('genomics', REQUEST_URI, read_variants(args.file))
    variants.set_null_str(args.nullStr)
    variants.set_page_size(args.pageSize)

    warning("Looking up ", variants.get_query_size(), "variants", prefix="INFO")
    
    variants.fetch()
    variants.write_response(file=stdout, format="json")

    