from fastapi import HTTPException
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.database.genomicsdb.schema.gene.documents import Gene as GeneORM


class GeneEndpointService(BaseEndpointService):
    _orm_model: GeneORM

    async def get_record_mappings(self, gene_ids: list[str]):
        mappings: RecordRetrievalResult = self._lookup_records(gene_ids)
        return {k: self._response_config.record_model(**v) for k, v in mappings}

    async def fetch_record(self, gene_id: str):
        # using mappings instead of fetch_record b/c fetching record is based
        # on exact match
        mappings = await self.get_record_mappings([gene_id])
        if not mappings[gene_id]:
            raise HTTPException(status_code=404, detail=f"Gene `{gene_id}` not found")
        return [self._response_config.record_model(**v) for v in mappings.values()]
