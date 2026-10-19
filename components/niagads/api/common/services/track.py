from fastapi import HTTPException
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.database.genomicsdb.schema.dataset.track import Track as TrackORM


class TrackEndpointService(BaseEndpointService):
    _orm_model = TrackORM

    async def get_record_mappings(self, track_ids: list[str]) -> dict:
        """Resolve track identifiers to configured response records.

        Args:
            track_ids (list[str]): Track identifiers to resolve.

        Returns:
            dict: Mapping of each identifier to its matching response records.
        """
        mappings: RecordRetrievalResult = await self._lookup_records(track_ids)
        return {
            identifier: [
                self._response_config.record_model(
                    **{**record, "id": record["source_id"]}
                )
                for record in records
            ]
            for identifier, records in mappings.items()
        }

    async def fetch_record(self, track_id: str) -> list:
        """Retrieve track records matching an identifier.

        Args:
            track_id (str): Track identifier to resolve.

        Returns:
            list: Matching track response records.

        Raises:
            HTTPException: If no matching track is found, with status code 404.
        """
        mappings = await self.get_record_mappings([track_id])
        if not mappings[track_id]:
            raise HTTPException(status_code=404, detail=f"Track `{track_id}` not found")
        return mappings[track_id]
