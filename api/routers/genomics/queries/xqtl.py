
from typing import List

from api.models.query_defintion import QueryDefinition

from api.routers.genomics.models.feature_score import xQTL

"""SELECT * FROM Results.QTL WHERE protocol_app_node_id = :id"""
# TODO: build variant & gene -> need gene_symbol ,ensembl_id

class TrackQTLQuery(QueryDefinition):
    name = 'xqtl-track-top-hits'
    query = """"""
    resultType = List[xQTL]
    bindParameters = ['id']
    fetchOne = False
    errorOnNull = "xQTL track not found in the NIAGADS Alzheimer's GenomicsDB"