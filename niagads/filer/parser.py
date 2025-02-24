import logging
from urllib.parse import unquote
from os.path import basename

from ..utils.list import array_in_string, remove_duplicates, drop_nulls
from ..utils.dict import prune
from ..utils import string as str_utils
from ..utils import reg_ex as re

def metadata_parser(metadata):
    ''' iterate over list of one or more raw metadata 
    objects from FILER API and standardize; returns array of standardized metadata objects'''
    return [ FILERMetadataParser(m).parse() for m in metadata ]


def split_replicates(replicates):
    if str_utils.is_null(replicates, True):
        return None
    
    if str_utils.is_non_numeric(replicates) and ',' in replicates:
        return replicates.replace(' ', '').split(',')
    
    return [str(replicates)] # covert to list of 1 string


def is_searchable_string(key, value, skipFieldsWith):
    """ 
        checks to see if key: value field contains, searchable text
        based on 1) field name and 2) field contents 
    """
    
    if isinstance(value, dict):
        return False
    
    if isinstance(value, list):
        raise NotImplementedError("need to handle nested string values when looking for searchable text")
    
    if array_in_string(key, skipFieldsWith):
        return False
    
    if value is None:
        return False
    
    if str_utils.is_bool(value):
        return False
    
    if str_utils.is_number(value):
        return False
    
    return True


class FILERMetadataParser:
    ''' parser for FILER metadata:
    standardizes keys, extracts non-name info from name, cleans up
    
        keys:
            -- replace spaces with _
            -- lower case
            -- camelCase to snake_case
            -- rename fields, e.g., antibody -> antibody_target
            -- remove (s)
        
        values:
            -- genome build: hg38 -> GRCh38, hg19 -> GRCh37
            -- build biosample object
            -- build file info object
            -- build data source object
            -- extract [] fields from trackName
            -- original trackName --> description
            -- add feature type
            -- remove TF etc from assay
    
    '''
    
    def __init__(self, data:dict = None, debug:bool=False):
        self.logger = logging.getLogger(__name__)
        self._debug = debug
        
        self.__metadata = data

        self.__datesAsStrings = False
        self.__biosamplePropsAsJson = False

        self.__filerDownloadUrl = None
        self.__primaryKeyLabel = None
        
        self.__searchableTextValues = [] # needed to save biosample info, if converting to JSON
        
        self.__biosampleMapper = None
        
        
    def set_biosample_mapper(self, mapper: list):
        self.__parse_biosample_mapper(mapper)
        
        
    def set_metadata(self, data):
        self.__metadata = data
        
        
    def set_dates_as_strings(self):
        self.__datesAsStrings = True
        
        
    def set_biosample_props_as_json(self):
        self.__biosamplePropsAsJson = True
        
        
    def set_primary_key_label(self, pkLabel: str):
        """ default is 'identifier', use to override """
        self.__primaryKeyLabel = pkLabel
        
        
    def set_filer_download_url(self, url):
        """ set value of FILER file download URL (base path) """
        self.__filerDownloadUrl = url
        

    def _get_metadata(self, attribute=None):
        """ for debugging, to access private member & also to handle KeyErrors"""
        if attribute is None:
            return self.__metadata
        
        else: 
            return self.__metadata[attribute] \
                if attribute in self.__metadata else None
    

    def __parse_biosample_mapper(self, mapper: list):
        """
        translates array of lines from biosample mapper file into hash

        Args:
            mapper (list): result from reading biosample mapper file into array   
        """
        # de type      
        # Proposed cell type      
        # Tissue of origin info   
        # Biosample info  
        # Life stage info 
        # Derivation info notes   
        # final cell type

        fields = { value: index for index, value in enumerate([str_utils.to_snake_case(x) for x in mapper.pop(0).split('\t')])}
        if mapper[-1] == '': mapper.pop()    # file may end with empty line
        
        self.__biosampleMapper = {}
        for row in mapper:
            entry = row.split('\t')
            mappedCellType = entry[fields['final_cell_type']]
            if mappedCellType: # check for empty string
                self.__biosampleMapper[entry[fields['original_cell_type']]] = mappedCellType
        


    def __parse_value(self, key, value):
        ''' catch numbers, booleans, nulls and html entities (b/c of text search) '''
        if str_utils.is_null(value, naIsNull=True):
            return None
        
        if str_utils.is_number(value):
            if 'replicate' in key.lower():
                return value # leave as string
            else:
                return str_utils.to_numeric(value)
        
        if 'date' in key.lower() and str_utils.is_date(value):
            return str_utils.to_date(value, returnStr=self.__datesAsStrings)

            
        return unquote(value) # html entities
    
    
    # TODO map ontology terms to correct     
    # TODO validate ontology terms against GenomicsDB
    # TODO handle tissue categories, systems to be list
    def __parse_biosamples(self):
        ''' "cell type": "Middle frontal area 46",
        "Biosample type": "Tissue",
        "Biosamples term id": "UBERON:0006483",            
        "Tissue category": "Brain",
        "Track Description": "Biosample_summary=With Cognitive impairment; middle frontal area 46 tissue female adult (81 years);Lab=Bradley Bernstein, Broad;System=central nervous system;Submitted_track_name=rep1-pr1_vs_rep1-pr2.idr0.05.bfilt.regionPeak.bb;Project=RUSH AD",
        "system category": "Nervous",
        "life stage": "Adult", '''
        
        # TODO - remove mapper; template files are now pre-mapped
        
        displayTerm = self._get_metadata("cell_type")
        biosampleType = self._get_metadata('biosample_type')
        cellLine = biosample if biosampleType == 'cell_line' else None
        trackDescription = self._get_metadata('track_description')
        biosampleSummary = re.regex_extract('Biosample_summary=([^;]*)', trackDescription ) \
            if trackDescription is not None else None
        biosample = re.regex_extract('premapping_cell_type=([^;]*)', trackDescription ) \
            if trackDescription is not None else None
        if biosample is None:
            biosample = displayTerm
    
        if displayTerm is not None and str_utils.is_number(displayTerm):
            self.logger.debug("Found numeric cell_type - " + str(displayTerm) + " - for track " + self._get_metadata('identifier'))
            displayTerm = unquote(self._get_metadata('file_name')).split('.')[0].replace(':',' - ')
            self.__metadata.update({'cell_type': displayTerm})
            self.logger.debug("Updated to " + displayTerm + " from file name = " + self._get_metadata('file_name'))
            
        biosampleCharacteristics  = {
            "biosample_term": str(biosample), 
            "biosample_term_id": self._get_metadata('biosamples_term_id'),
            "biosample_display": displayTerm, 
                # str(self.__biosampleMapper[biosample] if biosample in self.__biosampleMapper else biosample),
            "biosample_type": biosampleType.lower() if biosampleType is not None else None,
            "cell_line": cellLine,
            "tissue_category": self._get_metadata('tissue_category'),
            "system_category": self._get_metadata('system_category'),
            "life_stage" : self._get_metadata("life_stage"),
            "biosample_summary": self.__clean_list(biosampleSummary, delim=';')
        }
        
        biosampleCharacteristics = prune(biosampleCharacteristics, prune=['Unknown'])
        
        if self.__biosamplePropsAsJson:
            self.__metadata.update({"biosample_characteristics":  biosampleCharacteristics})
            self.__searchableTextValues = [self.__clean_text(v) 
                for k,v in biosampleCharacteristics.items() 
                if v is not None]
            self.__remove_attributes(['biosample_term', 'biosample_term_id', 
                'biosample_display', 'biosample_type', 'cell_line', 'life_stage',
                'tissue_category', 'system_category'])
        else:
            self.__metadata.update(biosampleCharacteristics)
        
            
    def __assign_feature_by_assay(self):
        assay = self._get_metadata('assay')
        if assay is not None:
            if 'QTL' in assay:
                return assay
            if 'TF' in assay:
                return "transcription factor binding site"
            if 'Histone' in assay:
                return "histone modification"
            if assay in ["Small RNA-seq", "short total RNA-seq"]:
                return "small non-coding RNA"   
            if assay in ['FAIRE-seq', 'DNase-seq', 'ATAC-seq']:
                return "chromatin accessibility"
            if assay == 'PRO-seq':
                return "enhancer"
            if assay in ['eCLIP', 'iCLIP', 'RIP-seq']:
                return "protein-RNA crosslink or binding sites"
        
        return None
    
    
    def __assign_feature_by_analysis(self):
        analysis = self._get_metadata('analysis')
        if analysis is not None:
            if analysis == "annotation":
                # check output type
                if 'gene' in self._get_metadata("output_type").lower():
                    return "gene"
                
                # check track_description
                # e.g., All lncRNA annotations
                trackDescription = self._get_metadata("track_description") 
                if trackDescription is not None and 'annotation' in trackDescription:
                    return re.regex_extract("All (.+) annotation" , self._get_metadata("track_description"))
            if 'QTL' in analysis:
                return analysis
        
        return None
    
    
    def __assign_feature_by_output_type(self):
        outputType = self._get_metadata("output_type")
        if 'enhancer' in outputType.lower():
            return "enhancer"    
        if 'methylation state' in outputType:
            state, loc = outputType.split(' at ')
            return loc + ' ' + state
        if 'microrna target' in outputType.lower():
            return 'microRNA target'  
        if 'microRNA' in outputType: 
            return "microRNA"     
        if 'exon' in outputType:
            return "exon"        
        if 'transcription start sites' in outputType or 'TSS' in outputType:
            return "transcription start site"      
        if 'transcribed fragments' in outputType:
            return 'transcribed fragment'
        
        if outputType in ["footprints", "hotspots"]:
            # TODO: this may need to be updated, as it varies based on the assay type
            return outputType
        
        # should have been already handled, but just in case
        if outputType in ["clusters", "ChromHMM", "Genomic Partition"]: 
            return None 
        
        if outputType.startswith("Chromatin"): # standardize case
            return outputType.lower()
        
        # peaks are too generic
        # TODO: handle peaks & correctly map, for now
        # just return
        # but there are some "enhancer peaks", which is why
        # this test is 2nd
        if 'peaks' in outputType:
            return outputType  
        
        return outputType
    
    
    def __assign_feature_by_classification(self):
        classification = self._get_metadata('classification').lower()
        if 'histone-mark' in classification:
            return "histone modification"
        if 'chip-seq' in classification or 'chia-pet' in classification:
            if 'ctcf' in classification:
                return 'CTCF-biding site'
            if 'ctcfl' in classification:
                return 'CTCFL-binding site'
            if classification.startswith('tf '):
                return 'transcription factor binding site'
            if 'chromhmm' in classification:
                return 'enhancer'
            
            # next options should have been  caught earier, but just in case
            assay = self._get_metadata('assay')
            if 'Histone' in assay:
                return 'histone modification'
            if 'TF' in assay:
                return 'transcription factor binding site'

        if classification == "rna-pet clusters":
            return "RNA-PET cluster"
        
        return None
    
        
    def __parse_feature_type(self): 
        feature = self.__assign_feature_by_assay()        
        if feature is None: feature = self.__assign_feature_by_analysis()
        if feature is None: feature = self.__assign_feature_by_classification() 
        if feature is None: feature = self.__assign_feature_by_output_type()

        if feature is None:
            raise ValueError("No feature type mapped for track: ", self.__metadata)
        
        # variants have unnecessary prefixes
        # SAS GIH INDEL
        # SAS GIH SNV
        # SAS GIH SV
        # SAS SV
        if feature.endswith(' INDEL'):
            feature = 'insertion/deletion variant (INDEL)'
        if feature.endswith(' SNV'):
            feature = 'single nucleotide variant (SNV)'
        if feature.endswith(' SV'):
            feature = 'structural variant (SV)'
            
        self.__metadata.update({"feature_type": feature})
        
        
    def __parse_data_category(self):
        category = self._get_metadata('assigned_data_category')
        if category is not None:
            category = category.lower()
            if category == 'called peaks expression': 
                category = 'called peaks'
            if category == 'qtl':
                category = 'QTL'
            
            self.__metadata.update({"data_category": category})
        

    def __parse_assay(self):
        analysis = None

        classification = self._get_metadata('classification')
        if classification == 'ChIP-seq consolidated ChromHMM':
            analysis = 'ChromHMM'
            
        assay = self._get_metadata('assay')

        if assay is not None:
            assay = assay.replace('-Seq', '-seq') # consistency 
            
            if 'ChromHMM' in assay:
                analysis = assay
                assay = "ChIP-seq"
                
            elif assay.lower() == 'annotation':
                assay = None
                analysis = "annotation"
            
            elif assay in ["eQTL", "sQTL"]:
                analysis = assay
                assay = None
            
            # TODO: need to check output type b/c assay type may need to be updated
            # e.g. DNASeq Footprinting if output_type == footprints
            elif 'DNase' in assay:
                return "DNase-seq"

        self.__metadata.update({"assay": assay, "analysis": analysis})


    def __parse_name(self):
        #     "trackName": "ENCODE Middle frontal area 46 (repl. 1) TF ChIP-seq CTCF IDR thresholded peaks (narrowPeak) 
        # [Experiment: ENCSR778NDP] [Orig: Biosample_summary=With Cognitive impairment; middle frontal area 46 tissue female adult (81 years);Lab=Bradley Bernstein, Broad;System=central nervous system;Submitted_track_name=rep1-pr1_vs_rep1-pr2.idr0.05.bfilt.regionPeak.bb;Project=RUSH AD] [Life stage: Adult]",
        
        name:str = self._get_metadata('track_name')

        if name is None: # take the file name and remove underscores, extension
            name = self.__parse_internal_url(self._get_metadata('processed_file_download_url'))
            name = basename(name)
            name = name.replace('.bed.gz', '').replace('_', ' ')
            self.__metadata.update({"name": name, "description": name })
        else:
            """
            remove paranthetical notes
            
            split points:
            bed*
            broadPeak
            idr_peak
            narrowPeak
            tss_peak
            
            pattern adapted from: https://stackoverflow.com/a/68862249 to only match closest parentheses
            """
        
            pattern = r"\s[(\[][^()\[\]]*?eak\)\s|\s\(bed[^()\[\]]*[)\]]\s"
            name = re.regex_split(pattern, name)
        
            self.__metadata.update({"name": name[0], "description": self._get_metadata('track_name') })


    def __parse_experiment_info(self):
        # [Experiment: ENCSR778NDP] [Orig: Biosample_summary=With Cognitive impairment; middle frontal area 46 tissue \
        # female adult (81 years);Lab=Bradley Bernstein, Broad;System=central nervous system; \
        # Submitted_track_name=rep1-pr1_vs_rep1-pr2.idr0.05.bfilt.regionPeak.bb;Project=RUSH AD]",
        id = self._get_metadata('encode_experiment_id')
        info = self.__clean_list(self._get_metadata('track_description'), delim=";")
        
        studyId = None
        studyLabel = None
        datasetId = None
        pubmedId = None 
        sampleGroup = None
        
        if info is not None:
            project = re.regex_extract('Project=([^;]*)', info)    
            studyId = re.regex_extract('study_id=([^;]*)', info) 
            
            studyName = re.regex_extract('study_name=([^;]*)', info) 
            if studyName is None:
                studyName = re.regex_extract('study_label=([^;]*)', info) 
                
            datasetId = re.regex_extract('dataset_id=([^;]*)', info) 
            pubmedId = re.regex_extract('study_pubmed_id=([^;]*)', info) 
            sampleGroup = re.regex_extract('sample_group=([^;]*)', info) 

        self.__metadata.update({
            "experiment_id": id,
            "experiment_info": info,
            "project": project,
            "study_id": studyId,
            "study_name": studyName,
            "dataset_id": datasetId,
            "pubmed_id": f'PMID:{pubmedId}' if pubmedId is not None and pubmedId != 'TBD' else None,
            "sample_group": sampleGroup
        })
        

    def __parse_data_source(self):
        source = self._get_metadata('data_source')
        if source.startswith('ADSP'):
            source = source.replace('_', ' ')
            version = None
        else:
            dsInfo = source.split('_', 1)
            source = dsInfo[0]
            version = dsInfo[1] if len(dsInfo) > 1 and dsInfo[0] else None
            
            if source == 'FANTOM5' and 'slide' in self._get_metadata('link_out_url'):
                version = version + '_SlideBase'
                
            if array_in_string(source, ['INFERNO', 'eQTL']):
                # don't split on the _
                source = self._get_metadata('data_source').replace('_', ' ')
                version = None
        
        self.__metadata.update( {
            "data_source": source,
            "data_source_version": version
        })
    
    
    def __parse_file_format(self):
        formatInfo = self._get_metadata('file_format').split(' ')
        format = formatInfo[0]      
        schema = None
        
        if len(formatInfo) == 1:
            if 'bed' in format:
                schema = format
                format = 'bed'    
        else:
            schema = formatInfo[1] if len(formatInfo) == 2 else formatInfo[1] + "|" + formatInfo[2]
            
        self.__metadata.update({"file_format": format, "file_schema": schema})
    
    
    def __parse_generic_url(self, url):
        ''' handle common fixes to all URL fields '''
        
        if url is not None and 'wget' in url:
            url = url.split(' ')[1]
            
        return url
    
    
    def __parse_internal_url(self, url):
        ''' correct domain and other formatting issues
        ''' 
        url = self.__parse_generic_url(url)           
        return re.regex_replace(r'^[^GADB]*\/GADB', self.__filerDownloadUrl, url)
    
    
    def __parse_urls(self):
        self.__metadata.update({
                "url": self.__parse_internal_url(self._get_metadata('processed_file_download_url')),
                "raw_file_url": self.__parse_internal_url(self._get_metadata('raw_file_download')),
                "download_url": self.__parse_generic_url(self._get_metadata('raw_file_url'))
        })
        

    def __parse_genome_build(self):
        genomeBuild = self._get_metadata('genome_build')
        if genomeBuild is not None:
            genomeBuild = 'GRCh38' if 'hg38' in genomeBuild else 'GRCh37'
        self.__metadata.update({"genome_build": genomeBuild})
    
    
    def __parse_is_lifted(self):
        genomeBuild = self._get_metadata('genome_build')
        dataSource = self._get_metadata('data_source')
        
        lifted = False
        if genomeBuild is not None:
            lifted = 'lifted' in genomeBuild
        
        if not lifted and dataSource is not None:
            lifted = 'lifted' in dataSource

        self.__metadata.update({"is_lifted": lifted})


    def __parse_output_type(self):
        outputType = self._get_metadata('output_type')
        if outputType.lower() in ['chromatin interactions', 'genomic partition', 'enhancer peaks']:
            outputType = outputType.lower()

        self.__metadata.update({"output_type": outputType})   
        
        
    def __clean_text(self, s:str):
        """
        clean text to remove symbols (;:,) and extra spaces 
        Args:
            value (str): string to clean
        Returns:
            cleaned string
        """
        cleanStr = re.regex_replace(';|,|:', '', s)
        return ' '.join(cleanStr.split()) # hack to remove multiple consecutive spaces
        
        
    def __clean_list(self, s:str, delim:str=';'):
        """
        wrapper to clean ';' delimited list of values; removes extra spaces
        can change delimiter w/ delim option

        Args:
            s (str): string to clean
            delim (str, optional): new delimiter. Defaults to ';'.
        """
        if s is None:
            return s

        cleanStr = s.replace('; ', ';')
        return delim.join(cleanStr.split(';')) # hack to remove multiple consecutive spaces
       
        

    def __add_text_search_field(self):
        """ concatenate everything that isn't a date or url """
        skipFieldsWith = ['date', 'url', 'md5', 'path', 'file', 'description']
        
        # sum(list, []) is a python hack for flattening a nested list
        textValues = [self.__clean_text(v) for k,v in self.__metadata.items() 
                if is_searchable_string(k, v, skipFieldsWith)]

        # some field have the same info
        self.__metadata.update({"searchable_text": ';'.join(remove_duplicates(textValues + self.__searchableTextValues))})
        

    def __rename_key(self, key):
        match key:
            case 'antibody':
                return 'antibody_target'
            case 'downloaded_date':
                return 'download_date'
            case 'processed_file_md5':
                return 'md5sum'
            case 'raw_file_md5':
                return 'raw_file_md5sum'
            case 'technical_replicate': # for consistency
                return 'technical_replicates'
            case 'date_added_to_filer':
                return 'filer_release_date'
            case _:
                return key
            

    def __transform_key(self, key):
        # camel -> snake + lower case
        tValue = str_utils.to_snake_case(key)
        tValue = tValue.replace(" ", "_")
        tValue = tValue.replace("(s)", "s")
        tValue = tValue.replace('#', '')
        return self.__rename_key(tValue)
        
        
    def __transform_key_values(self):
        ''' transform keys and since iterating over 
            the metadata anyway, catch nulls, numbers and convert from string
        '''
        self.__metadata = { self.__transform_key(key): self.__parse_value(key, value) for key, value in self.__metadata.items()}
        

    def __remove_attributes(self, attributes):
        """ remove attributes by name/key """    
        # add check b/c chance a key could have been removed earlier
        [self.__metadata.pop(key) for key in attributes if key in self.__metadata]

    def __remove_internal_attributes(self):
        ''' remove internal attributes '''
        internalKeys = ['link_out_url', 'processed_file_download_url', 'track_name', 'assigned_data_category',
                'track_description', 'wget_command', 'tabix_index_download', 'encode_experiment_id',
                'cell_type', 'biosamples_term_id', 'filepath', 'raw_file_download']
        
        self.__remove_attributes(internalKeys)
        

    def __update_primary_key_label(self):
        """ change label of primary key field from 'identifier' to value of self.__primaryKeyLabel """
        if self.__primaryKeyLabel is not None:
            self.__metadata.update({self.__primaryKeyLabel: self._get_metadata('identifier')})
            self.__remove_attributes(['identifier'])

    def __clean_qtl_text(self):
        """ xQTL track names/descriptions have consecutive duplicate text: 
        e.g. NG00102_Cruchaga_pQTLs Cerebrospinal fluid pQTL pQTL INDEL nominally significant associations
        remove the duplicate feature type from the text field
        """
        featureType = self._get_metadata('feature_type')
        if 'QTL' in featureType:
            self.__metadata.update({
                'name': self._get_metadata('name').replace(f'${featureType} ${featureType}', featureType),
                'description': self._get_metadata('description').replace(f'${featureType} ${featureType}', featureType),
                'searchable_text': self._get_metadata('searchable_text').replace(f'${featureType} ${featureType}', featureType),
            })


    def __final_patches(self):   
        # misc corrections to the data  
        # update primary key label
        self.__update_primary_key_label()    
        self.__clean_qtl_text()
    
        
    def parse(self):
        ''' parse the FILER metadata & transform/clean up 
        returns parsed / transformed metadata 
        
        if verifyTrack = True will query FILER to make sure that the track exists
        parser will return None if the track is not valid
        '''
        
        if self.__metadata is None:
            raise ValueError("Must set metadata before parsing FILERMetadataParser.set_metadata()")
        
        
        # standardize keys & convert nulls & numbers from__parse_replicates string
        self.__transform_key_values()
                        
        # parse concatenated data points into separate attributes
        # standardize others (e.g., urls, data sources)
        # dropping description; allow use cases to piece together out of the other info
        self.__parse_is_lifted()
        self.__parse_genome_build()
        self.__parse_data_source()
        self.__parse_biosamples()
        self.__parse_urls()
        self.__parse_file_format()
        self.__parse_experiment_info()
        self.__parse_name()
        self.__parse_assay()
        self.__parse_data_category()
        self.__parse_feature_type()
        self.__parse_output_type()
        
        # remove private info
        self.__remove_internal_attributes()
        # generate text search field
        self.__add_text_search_field()
        
        # patchees
        self.__final_patches()

        # return the parsed metadata
        return self.__metadata
