
from typing import List

from api.models.query_defintion import QueryDefinition

from api.routers.genomics.models.feature_score import xQTL

class xQTLResult(QueryDefinition):
    name = 'xqtl-track-top-hits'
    query = """"""
    useIdCTE = False
    resultType = List[xQTL]
    bindParameters = ['id']
    fetchOne = False
    errorOnNull = "xQTL track not found in the NIAGADS Alzheimer's GenomicsDB"