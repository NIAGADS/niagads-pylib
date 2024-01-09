##
# @package niagads.reference
# @file chromosomes.py
# @brief enums defining chromomosomes
# NOTE must install enum34 (backport of enum) to iterate over the enum object in python 2.7

from enum import Enum 
class Human(Enum):
    # name, value pair
    # e.g., for chr in Chromosome: print(chr.name)
    # will print a new line sep list of chr1 chr2 chr3, etc
    # print(chr.value) will print 1 2 3, etc.
    chr1 = 1
    chr2 = 2
    chr3 = 3
    chr4 = 4
    chr5 = 5
    chr6 = 6
    chr7 = 7
    chr8 = 8
    chr9 = 9
    chr10 = 10
    chr11 = 11
    chr12 = 12
    chr13 = 13
    chr14 = 14
    chr15 = 15
    chr16 = 16
    chr17 = 17
    chr18 = 18
    chr19 = 19
    chr20 = 20
    chr21 = 21
    chr22 = 22
    chrX = 'X'
    chrY = 'Y'
    chrM = 'M'
