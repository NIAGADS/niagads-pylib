from niagads.api.common.services.base import BaseEndpointService
from niagads.database.genomicsdb.schema.gene.documents import Gene


class GeneEndpointService(BaseEndpointService):
    _orm_model: Gene

    async def _retrieve_records(self, lookup_value):
        result = await super()._retrieve_records(lookup_value)
