# looks up a list of variants provided in a file
# returns as JSON or tab-delimited text
# output is to STDOUT
# author: fossilfriend

import requests
import argparse
import json
from sys import stderr, stdout, exit
from urllib.parse import urlencode
from multiprocessing import Pool

REQUEST_URI = "https://api.niagads.org"
GENOME_WIDE_SIG_P = 5e-8


# some helpers

def xstr(value, nullStr="", falseAsNull=False):
    """wrapper for str() that handles Nones

    Args:
        value (obj): value to be converted to string
        nullStr (str, optional): value to be printed for NULLS/None. Defaults to "".
        falseAsNull (bool, optional): treat boolean "False" as None. Defaults to False.

    Returns:
        string conversion of `value`
    """
    if value is None:
        return nullStr
    elif falseAsNull and isinstance(value, bool):
        if value is False:
            return nullStr
        else:
            return str(value)
    elif isinstance(value, list):
        return ','.join([xstr(v) for v in value])
    elif isinstance(value, dict):
        if bool(value):
            return json.dumps(value, sort_keys=True)
        else:
            return nullStr
    else:
        return str(value)
    

def pretty_print(obj):
    """ pretty print a dict 

    Args:
        obj (dict): object (dict) to be printed
    """
    if isinstance(obj, dict):
        print(json.dumps(obj, sort_keys=True, indent=4))
    else:
        print(obj)
    
    
def chunker(seq, size):
    """
    for a given sequence, splits into even + residual chunks.  returns an iterator 
    see: https://stackoverflow.com/a/434328
    using this to page the queries as paging is not yet implemented in the API

    Args:
        seq (tuple or list): list to be chunked
        size (integer): chunk size

    Returns:
        list of chunks
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

    
def make_request(endpoint, params):
    """
    wrapper to build and make a request against the NIAGADS API
    includes error check

    Args:
        endpoint (string): endpoint to be queried
        params (dict): dict of param_name:value pairs

    Raises:
        requests.exceptions.HTTPError on error

    Returns:
        JSON response if successful
    """

    requestUrl = REQUEST_URI + "/" + endpoint 
    if params is not None:
        requestUrl += '?' + urlencode(params)

    try:
        response = requests.get(requestUrl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print("HTTP Error: " + err.args[0])
        raise requests.exceptions.HTTPError
        

## end helpers


## response parsers 

def extract_allele_frequencies(annotation, skip='1000Genomes'):
    """extract allele frequencies and return as // delimited list 
    info strings reporting the freq for each population in a datasource

    Args:
        annotation (dict): variant annotation block
        skip (string, optional): A data source to skip. Defaults to '1000Genomes'.
    
    TODO:
        make `skip` a list of one or more datasources

    Returns:
        a string that uses // to delimitate an info string for each data source
        info strings are semi-colon delimited population=freq pairs
    """
    alleleFreqs = annotation['allele_frequencies']
    if alleleFreqs is None:
        return None
    else:
        freqs = []
        for source, populations in alleleFreqs.items():
            if skip is not None and source == skip:
                continue    
                  
            sFreqs = ["source=" + source]
            for pop, af in populations.items():
                sFreqs = sFreqs + ['='.join((pop, xstr(af)))] 
            freqs = freqs + [';'.join(sFreqs)]
            
        return '//'.join(freqs)    
        

def extract_1000Genomes_allele_frequencies(annotation):
    """extract out the 1000 Genomes frequencies into an array of freq,
        with one value for each population: 
             ['afr', 'amr', 'eas', 'eur', 'sas', 'gmaf']
    Args:
        annotation (dict): variant annotation block

    Returns:
        array of frequencies, with one value for each 1000 Genomes population
        if the population is not provided in the annotation, None is returned for
        that frequency
    """
    populations = ['afr', 'amr', 'eas', 'eur', 'sas', 'gmaf']
    alleleFreqs = annotation['allele_frequencies']
    if alleleFreqs  is None:
        return [None] * 6
    elif '1000Genomes' in alleleFreqs:
        freqs = alleleFreqs['1000Genomes']
        return [freqs[pop] if pop in freqs else None for pop in populations]
    else:
        return [None] * 6
    

def extract_associations(annotation):
    """ extract association (GWAS summary statistics resuls)
     from a variant annotations

    Args:
        annotation (dict): variant annotation block

    Returns:
        list containing:
            info string of dataset=pvalue pairs delimited by semicolons
            the # of associations
            the # of associations in which the p-value has genome wide significance
    """
    if annotation['associations'] is not None:
        associations = [key + '=' + str(value['p_value'])
                            for key, value in annotation['associations'].items()]
        associations.sort()
        
        # associations w/genome wide significance
        isGWS = [assoc['is_gws'] for assoc in annotation['associations'].values()]
        
        return [';'.join(associations), len(isGWS), sum(isGWS)]
    else:
        return [None, None, None]


def extract_consequences(conseqAnnotations, fields):
    """parse consequence annotations and retrieve the 
    consequence terms and qualifying information as specified by 
    `fields`

    Args:
        conseqAnnotations (dict): consequence annotation 
        fields (string list): list of fields to be extracted from the `conseqAnnotations`

    Returns:
         list containing:
            the consequence terms as a comma delimited string
            info string of annotation=value pairs delimited by a semi-colon
            if gene info (id or symbol) is requested (fields):
                also return gene_id, gene_symbol
    """
    conseq = ','.join(conseqAnnotations['consequence_terms'])   
    qualifiers = [ key + '=' + xstr(value, nullStr=args.nullStr) 
                    for key, value in conseqAnnotations.items() if key in fields and key not in ['gene_id', 'gene_symbol'] ]
    qualifiers.sort()
    
    if 'gene_id' in fields or 'gene_symbol' in fields:
        geneId = conseqAnnotations['gene_id'] \
            if 'gene_id' in fields and 'gene_id' in conseqAnnotations \
                else None
            
        geneSymbol = conseqAnnotations['gene_symbol'] \
            if 'gene_symbol' in fields and 'gene_symbol' in conseqAnnotations \
                else None
        return [conseq, ';'.join(qualifiers), geneId, geneSymbol]
            
    else:
        return [conseq, ';'.join(qualifiers)]


def extract_most_severe_consequence(annotation):
    """ extract most severe consequence and related annotations

    Args:
        annotation (dict): variant annotation block

    Returns:
        list containing:
            the consequence 
            info string of annotation=value pairs delimited by a semi-colon
    """
    fields = ['biotype', 'consequence_is_coding', 'impact', 'gene_id', 'gene_symbol', 'protein_id']   
    return extract_consequences(annotation['most_severe_consequence'], fields)


def extract_regulatory_feature_consequences(annotation):
    """extract regulatory feature consequences and related annotations

    Args:
        annotation (dict): variant annotation block

    Returns:
        // list of consequences and related annotations
        where each consequence and its annotations is returned as a info string of semi-colon
        delimited key=value pairs
    """
    rankedConsequences = annotation['ranked_consequences']
    if 'regulatory_feature_consequences'  in rankedConsequences:
        regConsequences = rankedConsequences['regulatory_feature_consequences']
        fields = ['biotype', 'impact', 'consequence_is_coding', 'impact', 'regulatory_feature_id', 'variant_allele']

        conseqList = [extract_consequences(conseqAnnotations, fields) for conseqAnnotations in regConsequences ]
        conseqs = ["consequence=" + conseq[0] + ";" + conseq[1] for conseq in conseqList]
        return '//'.join(conseqs)
    else:
        return None
    
    
def extract_motif_feature_consequences(annotation):
    """extract motif feature consequences and related annotations

    Args:
        annotation (dict): variant annotation block

    Returns:
        // list of consequences and related annotations
        where each consequence and its annotations is returned as a info string of semi-colon
        delimited key=value pairs
    """
    rankedConsequences = annotation['ranked_consequences']
    if 'motif_feature_consequences'  in rankedConsequences:
        motifConsequences = rankedConsequences['motif_feature_consequences']
        fields = ['impact', 'consequence_is_coding', 'impact', 'variant_allele',
                  'motif_feature_id', 'motif_name', 'motif_score_change', 'strand',
                  'transcription_factors']

        conseqList = [extract_consequences(conseqAnnotations, fields) for conseqAnnotations in motifConsequences ]
        conseqs = ["consequence=" + conseq[0] + ";" + conseq[1] for conseq in conseqList]
        return '//'.join(conseqs)
    else:
        return None



# end response parsers

def print_table(resultJson, reqChr):
    """print query result in tab-delimited text format to STDOUT

    Args:
        resultJson (dict): JSON response from query against webservice
        reqChr (boolean): flag indicating whether 'chr' needs to be prepended to the queried_varaint        
    """
    header = ['queried_variant', 'mapped_variant', 'ref_snp_id', 'is_adsp_variant',
              'most_severe_consequence', 'msc_annotations', 'msc_impacted_gene_id', 'msc_impacted_gene_symbol']
    if args.full:
        header = header + \
            ['CADD_phred_score', 
             'associations', 'num_associations', 'num_sig_assocations',
             'regulatory_feature_consequences', 'motif_feature_consequences']
        if args.alleleFreqs in ['1000Genomes', 'both']:
            header = header + \
                ['1000Genomes_AFR', '1000Genomes_AMR', '1000Genomes_EAS', 
                 '1000Genomes_EUR', '1000Genomes_SAS', '1000Genomes_GMAF']
        if args.alleleFreqs == 'all':
            header = header + ['allele_frequencies']
        if args.alleleFreqs == 'both':
            header = header + ['other_allele_frequencies']    
            
    print('\t'.join(header))
    
    for variant in resultJson:
        annotation = variant['annotation']
        
        values = ['chr' + variant['queried_variant'] if reqChr else variant['queried_variant'],
                  variant['metaseq_id'], variant['ref_snp_id'], variant['is_adsp_variant']] \
                    + extract_most_severe_consequence(annotation)

        if args.full: 
            values = values + [annotation['cadd_scores']['CADD_phred'] \
                if 'CADD_phred' in annotation['cadd_scores'] else None]
            values = values + extract_associations(annotation) 
            values = values + [extract_regulatory_feature_consequences(annotation)]
            values = values + [extract_motif_feature_consequences(annotation)]
            if args.alleleFreqs in ['1000Genomes', 'both']:
                values = values + extract_1000Genomes_allele_frequencies(annotation)
            if args.alleleFreqs in ['all', 'both']:
                skip = '1000Genomes' if args.alleleFreqs == 'both' else None
                values = values + [extract_allele_frequencies(annotation, skip)]

        print('\t'.join([xstr(v, nullStr=args.nullStr, falseAsNull=True) for v in values]))


def read_variants():
    """ read list of variants from file; removing 'chr' and
    substituting M for MT when appropriate
    removes header if found

    Returns:
        tuple of variants,
        flag indicating if 'chr' was removed so it can be added back later
    """
    with open(args.file) as fh:
        variants = fh.read().splitlines() 
        hasChr = True if 'chr' in variants[3] else False
        variants = [ v.replace('chr', '').replace('MT', 'M') for v in variants ]
        if variants[0].lower() in ['id', 'variant']:
            variants.pop(0)
    return tuple(variants), hasChr


def lookup(ids):
    """ loookup a list of variants by ID

    Args:
        ids (string list): list of variant identifiers

    Returns:
        json repsonse
    """
    return make_request("genomics/variant/", {"id": ','.join(ids), "full": args.full})


def run():
    """ run the lookup; since API currently does not
    do pagination; chunks the lookup list and submits requests in parallel
    using python mulitprocessing pooling

    Returns:
        json response for the lookup
    """
    chunks = chunker(variants, args.pageSize)
    with Pool() as pool:
        response = pool.map(lookup, chunks)
        return sum(response, []) # concatenates the individual responses


def main():
    parser = argparse.ArgumentParser(description="Look up a list of variants and retrieve annotation", allow_abbrev=False)
    parser.add_argument('--file', required=True,
                        help="new line separated list of variants, can be refSnpID or chr:pos:ref:alt")
    parser.add_argument('--format', default="json", choices=['table', 'json'], 
                        help="output file format; JSON format will include a lot more information than the table format")
    parser.add_argument('--pageSize', default=200, choices = [50, 200, 300, 400, 500], type=int)
    parser.add_argument('--full', help="retrieve full annotation; when not supplied will just return variant IDS and most severe consequence", action="store_true")
    parser.add_argument('--alleleFreqs', 
                        help="which allele frequencies to include in .tab format; `both` returns extracted 1000Genomes population frequencies & column with all others",
                        choices=['all', '1000Genomes', 'both'], default='1000Genomes')
    parser.add_argument('--nullStr', help="string for null values in .tab format", 
                        choices=['N/A', 'NA', 'NULL', '.', ''], default='')
    args = parser.parse_args()
    
    [variants, removeChr] = read_variants()
  
    print("Looking up", str(len(variants)), "variants.", file=stderr)
        
    result = run()
    if args.format == 'json':
        pretty_print(result)
    else:
        print_table(result, removeChr)