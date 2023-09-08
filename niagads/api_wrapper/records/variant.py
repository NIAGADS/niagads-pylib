import logging
from sys import stdout
from niagads.api_wrapper import constants
from niagads.api_wrapper.records import Record
from niagads.utils.string_utils import xstr

class Variant(Record):
    def __init__(self, requestUrl, database, variantIds=None):
        super().__init__(self, 'variant', requestUrl, variantIds)
        self.__full = False # retrieve full annotation?
        self.__alleleFrequencies = None
        self.__query_variants = None 
        self.set_ids(self._ids) # initializes query_variants
        
    def report_allele_frequencies(self, source="1000Genomes"):
        """
        report 1000Genomes frequencies only or all?

        Args:
            source (str, optional): one of `1000Genomes` or `all`. Defaults to "1000Genomes".
        """
        if source not in constants.ALLELE_FREQUENCIES:
            raise ValueError("Invalid allele frequency source: " + source 
                + "; valid values are: " + xstr(constants.ALLELE_FREQUENCIES))
        else:
            self.__alleleFrequencies = source
        
    def retrieve_full_annotation(self, flag=True):
        """
        retrieve full annotation? if set to false (default for variant lookups)
        only basic annotation: identifiers, most severe predicted consequence
        will be retrieved
        
        full annotation includes: ADSP QC, allele frequencies, CADD scores, 
        all predicted consequences

        Args:
            flag (bool, optional): flag indicating whether to retrieve full annotation. Defaults to True.
        """
        self.__full = flag
        
    def set_ids(self, ids):
        """
        overloads parent `set_ids` to clean variant ids 
        and create the user -> cleaned id mapping
        """
        self._ids = ids
        self.__query_variants = self.__parse_variant_ids(ids)

    def __clean_variant_id(self, id):
        """
        clean variant ids
            -- remove 'chr'
            -- replace 'MT' with 'M'
            -- replace 'RS' with 'rs'
            -- replace '/' with ':' (e.g., chr:pos:ref/alt)
            -- replace '_' with ':' (e.g., chr:pos:ref_alt)

        Args:
            id (string): variant identifier (expects rsId or chr:pos:ref:alt)

        Returns:
            _type_: _description_
        """
        return id.replace('chr', '').replace('MT','M') \
            .replace('RS', 'rs').replace('/', ':').replace('_', ':')
 
    def __parse_variant_ids(self, variantIds):
        """
        create mapping of user supplied variant id : cleaned id for lookups

        Args:
            queryVariants (string list): list of variants

        Returns:
            dict : cleaned id -> id mapping
        """
        return { self.__clean_variant_id(id): id for id in variantIds }
    
    def run(self):
        params = {} if self._params is None else self._params
        if self.__full is not None:
            self.set_params(params | {"full": self.__full})
        super().run()
        
    def write_response(self, file=stdout, format=None):
        if format is None:
            format = self._response_format
        if format == 'json':
            return super().write_response(file, format)
        else:
            return self.__write_tabular_response(file)
        
    def __write_tabular_response(self, file):
        """print query result in tab-delimited text format to STDOUT

        Args:
            resultJson (dict): JSON response from query against webservice
            reqChr (boolean): flag indicating whether 'chr' needs to be prepended to the queried_varaint        
        """
        header = ['queried_variant', 'mapped_variant', 'ref_snp_id', 'is_adsp_variant',
                'most_severe_consequence', 'msc_annotations', 'msc_impacted_gene_id', 'msc_impacted_gene_symbol']
        if self.__full:
            header = header + \
                ['CADD_phred_score', 
                'associations', 'num_associations', 'num_sig_assocations',
                'regulatory_feature_consequences', 'motif_feature_consequences']
            if self.__alleleFrequencies in ['1000Genomes', 'all']:
                header = header + \
                    ['1000Genomes_AFR', '1000Genomes_AMR', '1000Genomes_EAS', 
                    '1000Genomes_EUR', '1000Genomes_SAS', '1000Genomes_GMAF']
            if self.__alleleFrequencies == 'all':
                header = header + ['other_allele_frequencies']    
                
        print('\t'.join(header), file=file)
        
        resultJson = self.get_response()
        for variant in resultJson:
            annotation = variant['annotation']
            
            values = [self.__query_variants[variant['queried_variant']],
                      variant['metaseq_id'], variant['ref_snp_id'], variant['is_adsp_variant']] \
                        + extract_most_severe_consequence(annotation)

            if self.__full: 
                values = values + [annotation['cadd_scores']['CADD_phred'] \
                    if 'CADD_phred' in annotation['cadd_scores'] else None]
                values = values + extract_associations(annotation) 
                values = values + [extract_regulatory_feature_consequences(annotation)]
                values = values + [extract_motif_feature_consequences(annotation)]
                if self.__alleleFrequencies in ['1000Genomes', 'all']:
                    values = values + extract_1000Genomes_allele_frequencies(annotation)
                if self.__alleleFrequencies == 'all':
                    values = values + [extract_allele_frequencies(annotation, '1000Genomes')]

            print('\t'.join([xstr(v, nullStr=self._nullStr, falseAsNull=True) for v in values]), file=file)

    
# end class


## variant response parsers 

def extract_allele_frequencies(annotation, skip=['1000Genomes']):
    """extract allele frequencies and return as // delimited list 
    info strings reporting the freq for each population in a datasource

    Args:
        annotation (dict): variant annotation block
        skip (string, optional): A data source to skip. Defaults to '1000Genomes'.

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
            if skip is not None and source not in skip:
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
