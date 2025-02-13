##
# @package niagads.reference
# @file chromosomes.py
# @brief enums defining chromomosomes
# NOTE must install enum34 (backport of enum) to iterate over the enum object in python 2.7

from enum import Enum 
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
        
        