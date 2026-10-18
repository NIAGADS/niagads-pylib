from fastapi import HTTPException
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.database.genomicsdb.schema.gene.documents import Gene as GeneORM


class GeneEndpointService(BaseEndpointService):
    _orm_model = GeneORM

    async def get_record_mappings(self, gene_ids: list[str]):
        mappings: RecordRetrievalResult = await self._lookup_records(gene_ids)
        # self.logger.debug(mappings)
        return {
            k: [
                self._response_config.record_model(**mf) if mf else []
                for mf in mapped_features
            ]
            for k, mapped_features in mappings.items()
        }

    async def fetch_record(self, gene_id: str):
        # using mappings instead of fetch_record b/c fetching record is based
        # on exact match
        mappings = await self.get_record_mappings([gene_id])
        if not mappings[gene_id]:
            raise HTTPException(status_code=404, detail=f"Gene `{gene_id}` not found")

        # get_record_mappings handles building the 'records', so can just return
        # the mapped records
        return mappings[gene_id]
