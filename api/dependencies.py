from fastapi import Query
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from enum import Enum

from niagads.reference.chromosomes import Human as Chromosome

# https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#query-parameter-list-multiple-values

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


def chromosome_param(chromosome: str = Query(Chromosome.chr19.value, enum=[c.name for c in Chromosome],
        description="chromosome, specificed as 1..22,X,Y,M,MT or chr1...chr22,chrX,chrY,chrM,chrMT")):
    return Chromosome.validate(chromosome)
