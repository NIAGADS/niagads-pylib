import logging
from sys import stdout
from copy import deepcopy
from niagads.api_wrapper import constants, map_variant_conseq_types
from niagads.api_wrapper.records import Record
from niagads.utils.string_utils import xstr
from niagads.utils.dict_utils import get, dict_to_info_string

class VariantRecord(Record):
    def __init__(self, database, requestUrl="https://api.niagads.org", variantIds=None):
        super().__init__(self, 'variant', database, requestUrl, variantIds)
        self.__full = False # retrieve full annotation?
        self.__query_variants = None 
        self.set_ids(self._ids) # initializes query_variants


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
        
    
    def build_parser(self):
        if self._database == 'genomics':
            return GenomicsVariantRecordParser(self._database)
        else:
            return VariantRecordParser(self._database)   
        
                
    def write_response(self, file=stdout, format=None):
        if format is None:
            format = self._response_format
        if format == 'json':
            return super().write_response(file, format)
        else:
            return self.__write_tabular_response(file)
        
        
    def __write_tabular_response(self, file):
        if self._database == 'genomics':
            self.__write_genomics_tabular_response(file, self.build_parser())
        else:
            raise NotImplementedError("Writing tabular output not yet implemented for " + self._database + " variant records.")


    def __build_allele_frequence_array(self, freqs):
        if freqs is None:
            return [None * 7] 
        else:
            f10k = freqs.get('1000Genomes', None)
            if f10k is None:
                return [None * 6 ] + [dict_to_info_string(freqs)]
            else:
                pops = ['afr', 'amr', 'eas', 'eur', 'sas', 'gmaf']
                returnVal = [ f10k[p] for p in pops ] 
                del freqs['1000Genomes']
                return returnVal + [dict_to_info_string(freqs)]
            
 
    def __write_genomics_tabular_response(self, file, parser):
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
            parser.set_record(variant)

            values = [self.__query_variants[parser.get('queried_variant')],
                parser.get('metaseq_id'),
                parser.get('ref_snp_id'), 
                parser.get('is_adsp_variant')]
            
            msConseq = parser.get_consequences('most_severe')
            if msConseq is not None:
                terms = ','.join(msConseq.get('consequence_terms', None))
                del msConseq['consequence_terms']
                geneInfo = [None, None]
                if 'gene_id' in msConseq:
                    geneInfo[0] = msConseq['gene_id']
                    del msConseq['gene_id']
                if 'gene_symbol' in msConseq:
                    geneInfo[1] = msConseq['gene_symbol']
                    del msConseq['gene_symbol']
                values = values + [ terms, dict_to_info_string(msConseq), geneInfo]
            else:
                values = values + [None, None, None, None]
            
            
            annotation = parser.get('annotation')
            if self.__full and annotation is not None:
                caddScores = get(annotation, 'cadd_scores')
                values = values + [caddScores['CADD_phred'] \
                    if 'CADD_phred' in caddScores else None]
                
                values = values + [parser.get_associations(asString=True), 
                                   len(parser.get_associations()), # number associations
                                   len(parser.get_associations(genomeWideOnly=True))] # number of genome wide associations
                
                values = values + [parser.consequences('regulatory', asString=True)]
                values = values + [parser.get_consequences('motif', asString=True)]
                
                # TODO: fix allele frequencies reporting
                freqs = parser.get_allele_frequencies()
                values = values + [self.__build_allele_frequence_array(freqs)]

            print('\t'.join([xstr(v, nullStr=self._nullStr, falseAsNull=True) for v in values]), file=file)

    
# end class


## variant record  parsers 
class VariantRecordParser():
    def __init__(self, database, record=None):
        self.__database = database
        self.__record = None
        self.__annotation = None
        if record is not None:
            self.set_record(record) # handle error checking
            
    def get(self, attribute, default=None, errorAction='fail'):
        if self.__record is None:
            raise TypeError("record is NoneType")
        
        else:
            return get(self.__record, attribute, default, errorAction)
        
        
    def has_annotation_field(self):
        return self.__annotation is not None
        
        
    def set_record(self, record):
        if record is None:
            raise TypeError("Record is NoneType; cannot parse")
        self.__record = record
        self.__annotation = self.__record.get('annotation', None)   
        
    def get_record_attributes(self):
        return list(self.__record.keys())
    
    
    def get_annotation_types(self):
        if self.has_annotation_field():
            return list(self.__annotation.keys())
        else:
            raise AttributeError("Record has no annotation field or annoation is NoneType")

# end class

class GenomicsVariantRecordParser(VariantRecordParser):
    def __init__(self, database, record):
        super().__init__(database, record)

    
    def get_allele_frequencies(self, sources=[], asString=False):
        """get allele frequencies; if asString = True then return as // delimited list 
        info strings reporting the freq for each population in a datasource

        Args:
            sources (string list, optional): list of sources to retrieve. Defaults to []; returns all populations.
                --e.g., gnomAD, 1000Genomes
        Returns:
            frequency object or
            a string that uses // to delimitate an info string for each data source
            info strings are semi-colon delimited population=freq pairs
        """
        alleleFreqs = get(self.__annotation, 'allele_frequencies', None, 'ignore')
        if alleleFreqs is None:
            return None
        else:
            # note no way to validate sources b/c not all sources will be in all annotations
            # unless we store a reference array of valid sources
            
            sKeys = list(alleleFreqs.keys()) if len(sources) == 0 or sources is None else sources
            freqs = [] if asString else {}
            for source, populations in alleleFreqs.items():
                if source not in sKeys:
                    continue
        
                if asString:
                    sFreqs = dict_to_info_string(["source", source] + populations)
                    freqs = freqs + [sFreqs]
                else:
                    freqs[source] = populations
                
            return '//'.join(freqs) if asString else deepcopy(freqs)
        

    def get_associations(self, genomeWideOnly=False, asString=False):
        """ extract association (GWAS summary statistics resuls)
        from a variant annotations
        
        Args:
            asString (bool, optional): flag indicating whether or not to return info string. Defaults to False.
            genomeWideOnly (bool, optional): flag indicating whether to return genome wide assocs only
            
        Returns:
            if asString is False
                associations object
            else:
                info string of dataset=pvalue pairs delimited by semicolons         
        """
        associations = get(self.__annotation, 'associations')
        if associations is not None:
            if asString:
                if genomeWideOnly:
                    return dict_to_info_string({key : value['p_value'] 
                        for key, value in associations.item() 
                        if value['is_gws'] == 1})          
                else:
                    return dict_to_info_string({key : value['p_value'] for key, value in associations.item() })          
            else:
                if genomeWideOnly:
                    return {key : value
                        for key, value in associations.item() 
                        if value['is_gws'] == 1}
                else: 
                    return deepcopy(associations)
    

    def get_consequences(self, conseqType, asString=False):
        conseqAnnotations = None      
        if conseqType == 'most_severe':
            conseqAnnotations = get(self.__annotation, 'most_severe_consequence')
        else:
            conseqAnnotations = get(self.__annotation['ranked_conseqeunces'], map_variant_conseq_types(conseqType), None, 'ignore')
  
        if asString:
            conseq = deepcopy(conseqAnnotations)
            conseq['consequence_terms'] = ','.join(conseq['consequence_terms'])
            return dict_to_info_string(conseq)
        else:
            return conseqAnnotations


