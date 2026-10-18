from niagads.api.common.models.entities.gene.records import Gene
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.database.genomicsdb.schema.gene.documents import Gene as GeneORM


class GeneEndpointService(BaseEndpointService):
    _orm_model: GeneORM

    async def get_record_mappings(self, lookup_values: list[str]):
        mappings: RecordRetrievalResult = self._retrieve_records(lookup_values)
        return {k: Gene(**v) for k, v in mappings}
