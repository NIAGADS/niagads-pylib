from enum import Enum 
import csv
import logging
from niagads.string_utils.core import xstr

class Human(str, Enum):
    # name, value pair
    # e.g., for chr in Chromosome: print(chr.name)
    # will print a new line sep list of chr1 chr2 chr3, etc
    # print(chr.value) will print 1 2 3, etc.
    chr1 = '1'
    chr2 = '2'
    chr3 = '3'
    chr4 = '4'
    chr5 = '5'
    chr6 = '6'
    chr7 = '7'
    chr8 = '8'
    chr9 = '9'
    chr10 = '10'
    chr11 = '11'
    chr12 = '12'
    chr13 = '13'
    chr14 = '14'
    chr15 = '15'
    chr16 = '16'
    chr17 = '17'
    chr18 = '18'
    chr19 = '19'
    chr20 = '20'
    chr21 = '21'
    chr22 = '22'
    chrX = 'X'
    chrY = 'Y'
    chrM = 'M'
    
    
    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str): # allow 'X' or 'chrX'
        for member in cls:
            if value == member.name:
                return member
    
        raise KeyError(value)
    
        
    def __str__(self):
        return self.name
    
    
    @classmethod
    def sort_order(self):
        """ returns a {chr:order} mapping to faciliate chr based sorting"""
        return {chr: index for index, chr in enumerate(self.__members__)}
            
    @classmethod
    def validate(self, value:str, inclPrefix:bool=True):
        """
        validate a chromosome value against the enum; if match found will return match

        Args:
            value (str): value to match
            inclPrefix (bool, optional): include 'chr' prefix in the return. Defaults to True.
        """
        # make sure X,Y,M are uppercase; MT -> M 
        cv = str(value).upper().replace('CHR', '').replace('MT', 'M')
        if cv in self._value2member_map_:
            return 'chr' + cv if inclPrefix else cv
        return None
        
        
"""! @brief Chromosome Map Parser"""

##
# @brief  Parse and Access Chromosome Mappings
#
# @section chromosome_map_parser Description
# parses mappings of third party chromosome source ids (e.g., refseq) to chromosome number
# may also include chromosome length
# - for now assumes the tab-delim with at least the following columns:
# > source_id       chromosome     length
#
# @section todo_chromosome_map_parser TODO
# 
#
# @section libraries_chromosome_map_parser Libraries/Modules
# - cvs - reading and parsing the file
#
# @section author_chromosome_map_parser Author(s)
# - Created by Emily Greenfest-Allen (fossilfriend) 2022

class ChromosomeMapParser(object):
    """! Generator for chromosome map parser/object
    parses mappings of third party chromosome sequence ids (e.g., refseq) to chromosome number
    may also include chromosome length
    - for now assumes the tab-delim with at least the following columns:
    > source_id       chromosome     length      
    """
    
    def __init__(self, fileName, verbose=False, debug=False):
        """! ChromosomeMap base class initializer
            @param fileName             full path to chromosome mapping file
            @param verbose              verbose output flag
            @param debug                debug flag
            @return                     An instance of a ChromosomeMap with initialized mapping dict
        """
        self._verbose = verbose
        self._debug = debug
        self.logger = logging.getLogger(__name__)

        self.__file = fileName
        self.__map = {}
        self.__parse_mapping()
        
        
    def __parse_mapping(self):
        """! parse chromosome map
        """

        if self._verbose:
            self.logger.info("Loading chromosome map from:", self.__file)

        with open(self.__file, 'r') as fh:
            reader = csv.DictReader(fh, delimiter='\t')
            for row in reader:
                # source_id	chromosome	chromosome_order_num	length
                key = row['source_id']
                value = row['chromosome'].replace('chr', '')
                self.__map[key] = value
                        
    
    def chromosome_map(self):
        """! @returns                 the chromosome map
        """
        return self.__map
        
        
    def get_sequence_id(self, chrmNum):
        """! given a chromosome number, tries to find matching sequence id

            @param chrmNum             chromosome number to match
            @returns                   matching sequence id, None if not found
        """
        for sequenceId, cn in self.__map.items():
            if cn == chrmNum or cn == 'chr' + xstr(chrmNum):
                return sequenceId
            
        return None

            
    def get(self, sequenceId):
        """! return chromosome number mapped to the provided sequence ID

            @param sequenceId           sequence ID to look up
            @returns                    matching chrm number, will fail on error
        """
        # want to raise AttributeError if not in the map, so not checking
        return self.__map[sequenceId]
        
            