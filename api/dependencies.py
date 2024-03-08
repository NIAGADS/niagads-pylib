from fastapi import Query
from enum import Enum

RESPONSES = {404: {"description": "Not found"}}
class Assembly(str, Enum):
    """enum for genome builds"""
    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"
    hg19 = "hg19"
    hg38 = "hg38"
        
    @classmethod
    def validate(self, value):
        for e in self:
            if e.value.lower() == value.lower(): # for GRCh37/38 -> value match
                return "GRCh37" if value.lower() == 'hg19' else "GRCh38" if value.lower() == 'hg38' else e.value
    
        return None

def assembly_param(assembly: Assembly = Query(Assembly.GRCh38, description="reference genome build (assembly)")): 
    return Assembly.validate(assembly)

# https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#query-parameter-list-multiple-values
__CHR_NS = [str(x) for x in [*range(1,22)]] + ['X', 'Y', 'M']
__CHR_IDS = [ 'chr' + str(x) for x in __CHR_NS]
# __CHROMOSOMES = [*__CHR_NS, *__CHR_IDS]
Chromosome: Enum = Enum('Chromosome', { c.upper() : c for c in __CHR_IDS}, type=str)
def validate_chromosome(chrom: str | int):
    strC = str(chrom).upper().replace('CHR', 'chr').replace('MT', 'M')
    if strC in __CHR_IDS:
        return strC
    if strC in __CHR_NS:
        return 'chr' + strC
    return None

def chromosome_param(chrom = Query(Chromosome.CHR1, description="chromosome specified as")):
    return validate_chromosome(chrom)
    