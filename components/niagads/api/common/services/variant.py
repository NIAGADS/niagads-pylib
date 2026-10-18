from fastapi import HTTPException
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.database.genomicsdb.schema.variant.documents import Variant as VariantORM


class VariantEndpointService(BaseEndpointService):
    _orm_model = VariantORM

    async def get_record_mappings(self, variant_ids: list[str]) -> dict:
        """Retrieve variant records keyed by their requested identifiers.

        Args:
            variant_ids (list[str]): Variant identifiers to retrieve.

        Returns:
            dict: Mapping of each requested identifier to its response model.
        """
        mappings: RecordRetrievalResult = await self._lookup_records(variant_ids)
        return {
            identifier: self._response_config.record_model(**records[0])
            for identifier, records in mappings.items()
            if records
        }

    async def fetch_record(self, variant_id: str) -> list:
        """Retrieve a variant record or raise HTTP 404 when it is missing.

        Args:
            variant_id (str): Variant identifier to retrieve.

        Returns:
            list: Matching variant response records.

        Raises:
            HTTPException: If no variant matches the identifier.
        """
        mappings = await self.get_record_mappings([variant_id])
        if variant_id not in mappings:
            raise HTTPException(
                status_code=404, detail=f"Variant `{variant_id}` not found"
            )
        return [mappings[variant_id]]
