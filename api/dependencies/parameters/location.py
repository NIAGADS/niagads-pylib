from fastapi import Query
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from niagads.reference.chromosomes import Human as Chromosome
from niagads.utils.reg_ex import matches

from api.common.formatters import clean
from api.common.enums.base_enums import Assembly


async def assembly_param(assembly: Assembly = Query(Assembly.GRCh38, description="reference genome build (assembly)")): 
    try:
        return Assembly(clean(assembly))
    except:
        raise ResponseValidationError(f'Invalid value provided for `assembly`: {assembly}')

async def chromosome_param(chromosome: str = Query(Chromosome.chr19.value, enum=[c.name for c in Chromosome],
        description="chromosome, specificed as 1..22,X,Y,M,MT or chr1...chr22,chrX,chrY,chrM,chrMT")):
        return Chromosome.validate(clean(chromosome))

async def span_param(span: str = Query(alias="loc", description="genomic region to query; for a chromosome, N, please specify as chrN:start-end or N:start-end", examples=["chr19:10000-40000", "19:10000-40000"])):
    pattern =r'.+:\d+-\d+' # chr:start-enddddd - NOTE: the r prefix declares the pattern as a raw string so that no syntax warning gets thrown for escaping the d
    span = clean(span)
    
    # check against regexp
    if matches(pattern, span) == False:
        raise RequestValidationError(f'Invalid genomic span: `{span}`; for a chromosome, N, please specify as chrN:start-end or N:start-end')

    # split on :
    [chrm, coords] = span.split(':')
    validChrm = Chromosome.validate(chrm)
    if validChrm is None:
        raise RequestValidationError(f'Invalid genomic span: `{span}`; invalid chromosome `{chrm}`')

    # validate start < end
    [start, end] = coords.split('-')
    if (int(start) > int(end)):
        raise RequestValidationError(f'Invalid genomic span: `{span}`; start coordinate must be <= end')
    
    return validChrm + ':' + coords




