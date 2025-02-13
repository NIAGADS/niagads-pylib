from api.models.base_models import GenericDataModel

class VariantScore(GenericDataModel):
    variant_id: str
    
class GeneScore(GenericDataModel):
    gene_id: str
    