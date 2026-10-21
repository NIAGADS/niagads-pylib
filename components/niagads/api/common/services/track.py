from typing import Union

from fastapi import HTTPException
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.database.genomicsdb.schema.dataset.track import Track as TrackORM
from niagads.database.genomicsdb.schema.results.associations import (
    VariantAssociation as VAOrm,
)


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

    async def fetch_associations(
        self, track_id: str, *, summary: bool = False
    ) -> Union[list[VariantAssociation], list[DynamicRecord]]:
        """Retrieve variation associations for a stable track identifier.

        Args:
            track_id (str): Stable track identifier to resolve.
            summary (bool): Whether to return association counts by track.

        Returns:
            Union[list[VariantAssociation], list[DynamicRecord]]: Associations
                or per-track traits and counts; empty when no records match.
        """
        track_mapping = await self._lookup_records([track_id])
        if not track_mapping[track_id]:
            return []

        track_pk = track_mapping[track_id][0]["track_id"]
        mappings = await VAOrm.retrieve_records(
            self._context.database_session, track_pk
        )
        return self._generate_association_lookup_result(
            mappings[track_pk], summary=summary
        )
