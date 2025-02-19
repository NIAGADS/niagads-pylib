from api.models.query_defintion import QueryDefinition
from api.routers.genomics.models.feature_score import QTL, VariantPValueScore


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