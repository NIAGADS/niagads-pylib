from api.common.enums import RecordType
from api.models.base_models import SerializableModel

class RecordSearchResult(SerializableModel):
    id: str # primary_key (identifier) for the record (e.g., ensembl ID)
    description: str # descriptive text
    display: str # display id (e.g. gene symbol)
    record_type: RecordType # one of gene, variant, track, collection, etc
    matched_term: str
    match_rank: int