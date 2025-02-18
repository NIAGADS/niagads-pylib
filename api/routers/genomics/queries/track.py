
from typing import List

from api.models.query_defintion import QueryDefinition

from api.routers.genomics.models.feature_score import QTL, VariantPValueScore

"""SELECT * FROM Results.QTL WHERE protocol_app_node_id = :id"""
# TODO: build variant & gene -> need gene_symbol ,ensembl_id


TrackQTLQuery = QueryDefinition(
    query="""""",
    rowModel=QTL,
    useIdSelectWrapper=True,
    errorOnNull="xQTL track not found in the NIAGADS Alzheimer's GenomicsDB"
)
    
TrackGWASSumStatQuery = QueryDefinition(
    query = """""",
    rowModel=VariantPValueScore,
    useIdSelectWrapper=True,
    errorOnNull="GWAS summary statistics track not found in the NIAGADS Alzheimer's GenomicsDB"
)